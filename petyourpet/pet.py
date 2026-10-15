from __future__ import annotations

import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import platform_win


class Pet(QWidget):
    def __init__(self, renderer, cfg):
        super().__init__()
        self.renderer = renderer
        self.cfg = dict(cfg)
        self.frame = 0
        self.hovered = False
        self.moving = False
        self.user_hidden = False
        self.idle = None
        self.frames = []
        self.mask = None
        self.setWindowTitle("PetYourPet companion")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.animation = QTimer(self)
        self.animation.timeout.connect(self.advance)
        self.poll = QTimer(self)
        self.poll.setInterval(100)
        self.poll.timeout.connect(self.tick)
        self.configure(renderer, cfg)
        self.poll.start()
        app = QGuiApplication.instance()
        app.screenAdded.connect(self.screens_changed)
        app.screenRemoved.connect(self.screens_changed)
        self.connected_screens = set()
        self.connect_screens()

    def connect_screens(self):
        for screen in QGuiApplication.screens():
            if screen not in self.connected_screens:
                screen.availableGeometryChanged.connect(self.screens_changed)
                screen.geometryChanged.connect(self.screens_changed)
                self.connected_screens.add(screen)

    def selected_screen(self):
        return next((s for s in QGuiApplication.screens() if s.name() == self.cfg["screen"]),
                    QGuiApplication.primaryScreen())

    def screens_changed(self, *_):
        self.connect_screens()
        self.reposition()
        self.rebuild()

    def configure(self, renderer, cfg):
        self.renderer = renderer
        self.cfg = dict(cfg)
        top = self.cfg["mode"] == "top"
        desired = Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint
        if top:
            desired |= Qt.WindowStaysOnTopHint
        if self.windowFlags() != desired:
            visible = self.isVisible()
            self.setWindowFlags(desired)
            if visible:
                self.show()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.reposition()
        self.rebuild()
        platform_win.native_styles(int(self.winId()), False)
        self.tick()

    def rebuild(self):
        self.stop_petting()
        screen = self.selected_screen()
        area = screen.availableGeometry()
        rendered_cfg = dict(self.cfg)
        # Keep even very large hands/characters on small laptop displays.
        for _ in range(3):
            size = self.renderer.geometry(rendered_cfg)[0]
            factor = min(1., max(80, area.width() - 12) / size.width(),
                         max(80, area.height() - 12) / size.height())
            if factor >= .999:
                break
            rendered_cfg["height"] = max(12, rendered_cfg["height"] * factor * .98)
        self.idle, self.frames = self.renderer.frames(rendered_cfg, screen.devicePixelRatio())
        self.resize(self.idle.deviceIndependentSize().toSize())
        self.mask = self.idle.toImage()
        self.reposition()
        self.update()

    def reposition(self):
        screen = self.selected_screen()
        self.physical_screen = platform_win.screen_physical_rect(screen)
        area = screen.availableGeometry()
        x, y = self.cfg["x"], self.cfg["y"]
        if x is None or y is None:
            x = area.left() + 12
            y = area.bottom() - self.height() - 8
        x = max(area.left(), min(x, area.right() - self.width() + 1))
        y = max(area.top(), min(y, area.bottom() - self.height() + 1))
        self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        platform_win.native_styles(int(self.winId()), False)

    def paintEvent(self, event):
        if self.idle is None:
            return
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.frames[self.frame] if self.hovered else self.idle)

    def on_character(self, point):
        local = self.mapFromGlobal(point)
        if not self.rect().contains(local) or self.mask is None:
            return False
        x = int(local.x() * self.mask.width() / max(1, self.width()))
        y = int(local.y() * self.mask.height() / max(1, self.height()))
        return self.mask.pixelColor(x, y).alpha() > 12

    def tick(self):
        if self.moving:
            return
        visible = not self.user_hidden
        fg = platform_win.foreground() if visible else None
        if fg and fg[1] != os.getpid():
            (left, top, right, bottom), _ = fg
            screen_bounds = self.physical_screen
            if self.cfg["hide_fullscreen"] and screen_bounds:
                sl, st, sr, sb = screen_bounds
                if left <= sl + 2 and top <= st + 2 and right >= sr - 2 and bottom >= sb - 2:
                    visible = False
            if self.cfg["mode"] != "top":
                own = platform_win.physical_rect(int(self.winId()))
                if own and left < own[2] and right > own[0] and top < own[3] and bottom > own[1]:
                    visible = False
        if visible != self.isVisible():
            self.setVisible(visible)
        hover = visible and self.on_character(QCursor.pos())
        if hover and not self.hovered:
            self.hovered = True
            self.frame = 0
            self.animation.start(round(1000 / self.cfg["fps"]))
            self.update()
        elif not hover and self.hovered:
            self.stop_petting()

    def stop_petting(self):
        self.animation.stop()
        self.frame = 0
        self.hovered = False
        self.update()

    def advance(self):
        self.frame = (self.frame + 1) % len(self.frames)
        self.update()

