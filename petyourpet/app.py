from __future__ import annotations

import argparse
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtCore import QLockFile, QStandardPaths, Qt, QTimer, qVersion
from PySide6.QtGui import QAction, QFont, QFontDatabase, QGuiApplication, QIcon, QImageReader
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QMenu, QSystemTrayIcon

from . import __version__, platform_win
from .i18n import tr
from .pet import Pet
from .render import Renderer
from .storage import Store
from .ui import MoveDialog, PlacementWindow, SettingsDialog, STYLE


def assets_directory() -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / "assets"


class Controller:
    def __init__(self, app, store, cfg, assets, test_mode=False):
        self.app, self.store, self.cfg, self.assets = app, store, cfg, assets
        self.test_mode = test_mode
        self.first_setup = not store.path.exists()
        self.cfg["autostart"] = False if test_mode else platform_win.startup_enabled()
        self.renderer = Renderer(store.image(cfg, assets / "rufus.png"), assets / "hand.png")
        self.pet = Pet(self.renderer, cfg)
        self.settings = None
        self.move_dialog = None
        self.move_window = None
        self.tray = QSystemTrayIcon(QIcon(str(assets / "icon.ico")), app)
        self.tray.setToolTip("PetYourPet")
        self.tray.activated.connect(self.tray_activated)
        self.has_tray = QSystemTrayIcon.isSystemTrayAvailable()
        self.rebuild_menu()
        if self.has_tray:
            self.tray.show()

    def rebuild_menu(self):
        previous = getattr(self, "menu", None)
        self.menu = QMenu()
        self.menu.setStyleSheet(STYLE + "QMenu { background: #303c2c; border: 1px solid #809174; padding: 3px; } QMenu::item { padding: 6px 18px; } QMenu::item:selected { background: #506447; }")
        lang = self.cfg["language"]
        self.menu.addAction(tr("settings", lang), self.open_settings)
        self.menu.addAction(tr("show" if self.pet.user_hidden else "hide", lang), self.toggle_hidden)
        self.menu.addAction(tr("move", lang), self.start_move)
        self.menu.addAction(tr("home", lang), self.bring_home)
        self.menu.addSeparator()
        self.menu.addAction(tr("quit", lang), self.app.quit)
        self.tray.setContextMenu(self.menu)
        if previous is not None:
            previous.deleteLater()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.open_settings()

    def open_settings(self):
        if self.move_dialog:
            self.move_dialog.show()
            self.move_dialog.raise_()
            self.move_dialog.activateWindow()
            return
        if self.settings is None:
            self.settings = SettingsDialog(self.store, self.cfg, self.renderer, self.assets,
                                           self.preview, self.commit)
            self.settings.setWindowIcon(QIcon(str(self.assets / "icon.ico")))
            self.settings.move_requested.connect(self.start_move)
            self.settings.finished.connect(self.settings_finished)
            if not self.has_tray:
                self.settings.notice.setText(tr("no_tray", self.cfg["language"]))
                self.settings.notice.show()
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def preview(self, renderer, cfg):
        self.pet.configure(renderer, cfg)

    def commit(self, cfg, renderer):
        before = False if self.test_mode else platform_win.startup_enabled()
        startup_changed = not self.test_mode and cfg["autostart"] != before
        try:
            if startup_changed:
                platform_win.set_startup(cfg["autostart"])
        except OSError:
            logging.exception("Could not change startup")
            self.settings.error("startup_error")
            return False
        try:
            self.store.save(cfg)
        except OSError:
            logging.exception("Could not save settings")
            if startup_changed:
                try:
                    platform_win.set_startup(before)
                except OSError:
                    logging.exception("Could not restore startup after failed save")
            self.settings.error("write")
            return False
        self.cfg = dict(cfg)
        self.renderer = renderer
        self.store.warning = ""
        self.pet.configure(renderer, cfg)
        self.rebuild_menu()
        if self.first_setup and self.has_tray and not self.test_mode:
            self.tray.showMessage(tr("first", cfg["language"]), tr("tray_tip", cfg["language"]), QSystemTrayIcon.Information, 5000)
        self.first_setup = False
        return True

    def settings_finished(self, result):
        old = self.settings
        self.settings = None
        if result != QDialog.Accepted:
            self.pet.configure(self.renderer, self.cfg)
        old.deleteLater()
        if not self.has_tray:
            self.app.quit()

    def toggle_hidden(self):
        self.pet.user_hidden = not self.pet.user_hidden
        self.pet.tick()
        self.rebuild_menu()

    def bring_home(self):
        if self.move_dialog is not None:
            self.move_dialog.reject()
        self.open_settings()
        self.settings.cfg.update(x=None, y=None, screen=QGuiApplication.primaryScreen().name())
        self.settings.populate_screens()
        self.pet.user_hidden = False
        self.settings.apply_preview()

    def start_move(self):
        if self.move_dialog is not None:
            return
        self.open_settings()
        self.settings.debounce.stop()
        self.settings.apply_preview()
        self.move_before = {k: self.settings.cfg[k] for k in ("x", "y", "screen")}
        self.settings.hide()
        self.pet.poll.stop()
        self.pet.stop_petting()
        self.pet.moving = True
        self.pet.hide()
        self.move_window = PlacementWindow(self.pet.idle)
        self.move_window.move(self.pet.pos())
        self.move_dialog = MoveDialog(self.settings.cfg["language"])
        self.move_dialog.finished.connect(self.finish_move)
        self.move_window.placed.connect(self.move_dialog.accept)
        self.move_window.cancelled.connect(self.move_dialog.reject)
        self.move_dialog.adjustSize()
        area = self.pet.selected_screen().availableGeometry()
        self.move_dialog.move(area.center().x() - self.move_dialog.width() // 2, area.top() + 30)
        self.move_window.show()
        self.move_dialog.show()

    def finish_move(self, result):
        if self.move_window is None:
            return
        window = self.move_window
        screen = QGuiApplication.screenAt(window.geometry().center()) or self.pet.selected_screen()
        placement = {"x": window.x(), "y": window.y(), "screen": screen.name()}
        window.completed = True
        window.releaseMouse()
        window.hide()
        window.deleteLater()
        self.move_window = None
        self.pet.moving = False
        self.settings.cfg.update(placement if result == QDialog.Accepted else self.move_before)
        self.settings.populate_screens()
        self.settings.apply_preview()
        self.pet.poll.start()
        self.move_dialog.deleteLater()
        self.move_dialog = None
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()


def main(argv=None):
    parser = argparse.ArgumentParser(description="PetYourPet — a little desktop companion")
    parser.add_argument("--background", action="store_true", help="Start in the tray after first setup")
    parser.add_argument("--data-dir", type=Path, help="Use a separate settings directory (also isolates single-instance handling)")
    parser.add_argument("--test-mode", action="store_true", help="Never change Windows startup")
    parser.add_argument("--smoke-output", type=Path, help="Write a build health report and close automatically")
    parser.add_argument("--screenshot", type=Path, help="Save a settings preview image (for release screenshots)")
    parser.add_argument("--quit-after-ms", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("PetYourPet")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("PetYourPet")
    app.setQuitOnLastWindowClosed(False)
    for font in (assets_directory() / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont("IBM Plex Mono", 10))
    app.setWindowIcon(QIcon(str(assets_directory() / "icon.ico")))
    QImageReader.setAllocationLimit(128)
    store = Store(args.data_dir)
    log = RotatingFileHandler(store.root / "app.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[log], format="%(asctime)s %(levelname)s %(message)s", force=True)
    logging.info("PetYourPet %s, Python %s, Qt %s", __version__, sys.version.split()[0], qVersion())
    lock = QLockFile(str(store.root / "instance.lock"))
    server_name = "PetYourPet-" + hashlib.sha256(str(store.root.resolve()).lower().encode()).hexdigest()[:20]
    if not lock.tryLock(0):
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(1500):
            socket.write(b"show")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(server_name)
    server.setSocketOptions(QLocalServer.UserAccessOption)
    if not server.listen(server_name):
        logging.error("Could not start local instance channel: %s", server.errorString())
    cfg = store.load()
    controller = Controller(app, store, cfg, assets_directory(), args.test_mode or bool(args.smoke_output))

    def receive():
        while server.hasPendingConnections():
            client = server.nextPendingConnection()
            controller.open_settings()
            client.disconnectFromServer()
            client.deleteLater()
    server.newConnection.connect(receive)

    def exception_handler(kind, value, tb):
        logging.error("Unhandled exception", exc_info=(kind, value, tb))
        if args.smoke_output:
            app.exit(1)
            return
        QMessageBox.critical(None, "PetYourPet", tr("error", controller.cfg["language"]) + "\n" + str(value))
    sys.excepthook = exception_handler
    if not args.background or not store.path.exists() or not controller.has_tray or args.smoke_output or args.screenshot:
        controller.open_settings()

    def capture():
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            if not controller.settings.grab().save(str(args.screenshot)):
                raise OSError("Screenshot could not be written")
        if args.smoke_output:
            report = {"version": __version__, "qt": qVersion(), "frozen": bool(getattr(sys, "frozen", False)),
                      "tray": controller.has_tray, "frames": len(controller.pet.frames),
                      "window": [controller.settings.width(), controller.settings.height()],
                      "character_loaded": not controller.renderer.image.isNull(),
                      "hand_loaded": not controller.renderer.hand.isNull(),
                      "fonts_loaded": all(name in QFontDatabase.families() for name in ("Press Start 2P", "IBM Plex Mono")),
                      "native_click_through": bool(platform_win.get_style(int(controller.pet.winId()), -20) & 0x20) if platform_win.IS_WINDOWS and app.platformName() != "offscreen" else None}
            args.smoke_output.parent.mkdir(parents=True, exist_ok=True)
            args.smoke_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            app.quit()
    if args.smoke_output or args.screenshot:
        QTimer.singleShot(900, capture)
    if args.quit_after_ms:
        QTimer.singleShot(args.quit_after_ms, app.quit)

    try:
        return app.exec()
    finally:
        controller.pet.poll.stop()
        controller.pet.animation.stop()
        controller.tray.hide()
        server.close()
        lock.unlock()
        logging.shutdown()
