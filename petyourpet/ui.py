from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QSlider, QToolButton, QVBoxLayout, QWidget,
)

from .i18n import tr
from .render import FRAME_COUNT, Renderer
from .storage import DEFAULTS

STYLE = """
QWidget { color: #dce1d7; font-family: 'IBM Plex Mono'; font-size: 12px; font-style: normal; }
QDialog { background: #303632; }
QLabel { background: transparent; }
QLabel#brand { font-family: 'Press Start 2P'; font-size: 18px; font-weight: 400; color: #b3cd9e; }
QLabel#muted { color: #a4afa1; font-size: 11px; }
QLabel#eyebrow { color: #a4afa1; font-size: 10px; }
QLabel#section { font-size: 12px; font-weight: 600; color: #c2d6b3; }
QLabel#value { color: #c0d5a5; font-size: 11px; }
QLabel#notice { color: #ead3a0; font-size: 11px; background: #39382d; padding: 8px; border: 1px solid #777154; }
QFrame#card { background: #262c28; border-top: 1px solid #121a15; border-left: 1px solid #121a15; border-right: 1px solid #626e60; border-bottom: 1px solid #626e60; }
QFrame#rule { background: #171e19; border-bottom: 1px solid #52604f; max-height: 2px; }
QPushButton, QToolButton { background: #424d40; border-top: 1px solid #819078; border-left: 1px solid #819078; border-bottom: 1px solid #101810; border-right: 1px solid #101810; border-radius: 0; padding: 6px 11px; min-height: 19px; }
QPushButton:hover, QToolButton:hover { background: #50604a; }
QPushButton:pressed, QToolButton:pressed { background: #2c392b; border-top-color: #101810; border-left-color: #101810; border-bottom-color: #819078; border-right-color: #819078; padding-top: 7px; padding-bottom: 5px; }
QPushButton:focus, QToolButton:focus { color: #ffffff; }
QPushButton#primary { background: #9cb58b; color: #172014; border-top-color: #d0ddbf; border-left-color: #d0ddbf; font-weight: 600; padding-left: 17px; padding-right: 17px; }
QPushButton#primary:hover { background: #b3c99f; }
QPushButton#quiet { background: transparent; border-color: transparent; color: #aebba6; }
QPushButton#quiet:hover { color: #ebf1e3; background: #3a4636; }
QPushButton#edit:checked { color: #d4e9c5; background: #243222; border-top-color: #101810; border-left-color: #101810; border-bottom-color: #819078; border-right-color: #819078; }
QToolButton#disclosure { background: transparent; border: none; padding: 6px 0; text-align: left; color: #becdb3; }
QSlider { background: transparent; }
QCheckBox { spacing: 8px; padding: 3px 0; }
QCheckBox::indicator { width: 13px; height: 13px; border-radius: 0; background: #1d261e; border-top: 1px solid #101810; border-left: 1px solid #101810; border-right: 1px solid #819078; border-bottom: 1px solid #819078; }
QCheckBox::indicator:checked { background: #b3cc9d; border: 3px solid #253621; }
QComboBox { background: #232c22; border-top: 1px solid #101810; border-left: 1px solid #101810; border-right: 1px solid #819078; border-bottom: 1px solid #819078; border-radius: 0; padding: 6px 22px 6px 7px; min-height: 18px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #b4c4a8; }
QComboBox QAbstractItemView { background: #293726; color: #e4eddd; selection-background-color: #526d46; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: #303632; }
QScrollBar:vertical { background: #20281f; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #68785e; min-height: 30px; border-radius: 0; border-top: 1px solid #9cae91; border-left: 1px solid #9cae91; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QToolTip { background: #e1e3c7; color: #1b2119; border: 1px solid #101810; padding: 5px; }
"""


class SoftSlider(QSlider):
    """Consistent rendering on Windows styles and fractional DPI scales."""
    def __init__(self, orientation=Qt.Horizontal):
        super().__init__(orientation)
        self.setFixedHeight(28)
        self.setFocusPolicy(Qt.StrongFocus)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        start, end, y = 9., self.width() - 9., self.height() / 2
        fraction = (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum())
        x = start + (end - start) * fraction
        p.setPen(QPen(QColor("#161f16"), 3))
        p.drawLine(QPointF(start, y), QPointF(end, y))
        p.setPen(QPen(QColor("#9cb58b"), 3))
        p.drawLine(QPointF(start, y), QPointF(x, y))
        p.setPen(Qt.NoPen)
        if self.hasFocus():
            p.setPen(QPen(QColor("#b9d4a0"), 1, Qt.DotLine))
            p.drawRect(QRectF(x - 10, y - 11, 20, 22))
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(QRectF(x - 6, y - 8, 12, 16), QColor("#73866a"))
        p.setPen(QColor("#b7c6a8"))
        p.drawLine(QPointF(x - 6, y - 8), QPointF(x + 6, y - 8))
        p.drawLine(QPointF(x - 6, y - 8), QPointF(x - 6, y + 8))
        p.setPen(QColor("#162312"))
        p.drawLine(QPointF(x + 6, y - 8), QPointF(x + 6, y + 8))
        p.drawLine(QPointF(x - 6, y + 8), QPointF(x + 6, y + 8))
        p.drawLine(QPointF(x - 1, y - 4), QPointF(x - 1, y + 4))
        p.setPen(QColor("#b7c6a8"))
        p.drawLine(QPointF(x + 1, y - 4), QPointF(x + 1, y + 4))

    def set_from_position(self, x):
        fraction = max(0, min(1, (x - 9) / max(1, self.width() - 18)))
        self.setValue(round(self.minimum() + fraction * (self.maximum() - self.minimum())))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self.setSliderDown(True)
            self.set_from_position(event.position().x())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self.set_from_position(event.position().x())
            event.accept()

    def mouseReleaseEvent(self, event):
        self.setSliderDown(False)
        event.accept()

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class Preview(QWidget):
    changed = Signal(float, float)
    dropped = Signal(str)

    def __init__(self, renderer, cfg, parent=None):
        super().__init__(parent)
        self.renderer = renderer
        self.cfg = cfg
        self.frame = 0
        self.hovered = False
        self.editing = False
        self.light = False
        self.drag_body = None
        self.setMinimumSize(290, 280)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setAccessibleName("Pet preview")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(round(1000 / cfg["fps"]))

    def mapping(self):
        size, body, _ = self.renderer.geometry(self.cfg, 255)
        scale = min((self.width() - 30) / size.width(), (self.height() - 28) / size.height(), 1.35)
        offset = QPointF((self.width() - size.width() * scale) / 2, (self.height() - size.height() * scale) / 2)
        mapped = QRectF(offset.x() + body.x() * scale, offset.y() + body.y() * scale,
                        body.width() * scale, body.height() * scale)
        return scale, offset, mapped

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#d3d5c8" if self.light else "#252d27"))
        cell = 12
        shade = QColor("#c2c7b8" if self.light else "#2d352e")
        for x in range(0, self.width(), cell):
            for y in range(0, self.height(), cell):
                if (x // cell + y // cell) % 2:
                    p.fillRect(x, y, cell, cell, shade)
        scale, offset, body = self.mapping()
        p.save()
        p.translate(offset)
        p.scale(scale, scale)
        self.renderer.draw(p, self.cfg, 0 if self.editing else self.frame if self.hovered else None, 255)
        p.restore()
        if self.editing:
            point = QPointF(body.x() + body.width() * self.cfg["hand_x"],
                            body.y() + body.height() * self.cfg["hand_y"])
            p.setPen(QPen(QColor("#d2e8b5"), 1))
            p.setBrush(QColor("#34472c"))
            p.drawRect(QRectF(point.x() - 5, point.y() - 5, 10, 10))
            p.drawLine(point + QPointF(-13, 0), point + QPointF(13, 0))
            p.drawLine(point + QPointF(0, -13), point + QPointF(0, 13))

    def character_at(self, point):
        _, _, body = self.mapping()
        if not body.contains(point):
            return False
        u = (point.x() - body.left()) / body.width()
        v = (point.y() - body.top()) / body.height()
        if self.cfg["flip"]:
            u = 1 - u
        image = self.renderer.image
        x = min(image.width() - 1, max(0, int(u * image.width())))
        y = min(image.height() - 1, max(0, int(v * image.height())))
        return image.pixelColor(x, y).alpha() > 12

    def advance(self):
        self.hovered = self.character_at(self.mapFromGlobal(QCursor.pos()))
        if self.hovered and not self.editing:
            self.frame = (self.frame + 1) % FRAME_COUNT
            self.update()

    def mouseMoveEvent(self, event):
        if self.editing and event.buttons() & Qt.LeftButton:
            self.drag_to(event.position())
        else:
            old = self.hovered
            self.hovered = self.character_at(event.position())
            if old != self.hovered:
                self.frame = 0
                self.update()

    def mousePressEvent(self, event):
        if self.editing and event.button() == Qt.LeftButton:
            self.drag_body = self.mapping()[2]
            self.drag_to(event.position())

    def mouseReleaseEvent(self, event):
        self.drag_body = None

    def drag_to(self, point):
        body = self.drag_body or self.mapping()[2]
        x = max(-.25, min(1.25, (point.x() - body.x()) / body.width()))
        y = max(-.2, min(.65, (point.y() - body.y()) / body.height()))
        self.changed.emit(x, y)
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.frame = 0
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".png":
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            self.dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()

    def showEvent(self, event):
        self.timer.start(round(1000 / self.cfg["fps"]))

    def hideEvent(self, event):
        self.timer.stop()


class SettingsDialog(QDialog):
    move_requested = Signal()

    def __init__(self, store, cfg, renderer, assets, on_preview, on_commit, parent=None):
        super().__init__(parent)
        self.store, self.assets = store, assets
        self.cfg = dict(cfg)
        self.renderer = renderer
        self.on_preview, self.on_commit = on_preview, on_commit
        self.bindings = []
        self.sliders = {}
        self.setWindowTitle("PetYourPet")
        self.setStyleSheet(STYLE)
        self.setAcceptDrops(True)
        self.setMinimumSize(820, 610)
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(990, area.width() - 40), min(750, area.height() - 60))
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 18)
        root.setSpacing(16)
        header = QHBoxLayout()
        branding = QVBoxLayout()
        brand = QLabel("PetYourPet")
        brand.setObjectName("brand")
        branding.addWidget(brand)
        header.addLayout(branding, 1)
        root.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(26)
        card = QFrame()
        card.setObjectName("card")
        left = QVBoxLayout(card)
        left.setContentsMargins(10, 12, 10, 10)
        left.setSpacing(10)
        left.addWidget(self.label("preview", "eyebrow"))
        self.preview = Preview(renderer, self.cfg)
        self.preview.changed.connect(self.move_hand)
        self.preview.dropped.connect(self.import_png)
        left.addWidget(self.preview, 1)
        self.hint = self.label("hover", "muted")
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setWordWrap(True)
        left.addWidget(self.hint)
        background_row = QHBoxLayout()
        background_row.addStretch()
        for name, value in (("dark_bg", False), ("light_bg", True)):
            button = self.bind(QPushButton(), name)
            button.setAccessibleName("Light preview background" if value else "Dark preview background")
            button.clicked.connect(lambda checked=False, light=value: self.set_background(light))
            background_row.addWidget(button)
        background_row.addStretch()
        left.addLayout(background_row)
        drop_hint = self.label("drop", "muted")
        drop_hint.setWordWrap(False)
        drop_hint.setAlignment(Qt.AlignCenter)
        left.addWidget(drop_hint)
        columns.addWidget(card, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        right = QVBoxLayout(content)
        right.setContentsMargins(0, 0, 12, 0)
        right.setSpacing(11)
        right.addWidget(self.label("character", "section"))
        self.character_name = QLabel()
        self.character_name.setObjectName("muted")
        self.character_name.setWordWrap(True)
        right.addWidget(self.character_name)
        buttons = QHBoxLayout()
        choose = self.button("choose", self.choose_png)
        choose.setObjectName("primary")
        buttons.addWidget(choose)
        reset = self.button("default", self.default_character)
        reset.setObjectName("quiet")
        buttons.addWidget(reset)
        buttons.addStretch()
        right.addLayout(buttons)
        self.slider(right, "height", "size", 70, 500, " px")
        right.addWidget(self.rule())
        right.addWidget(self.label("petting", "section"))
        self.edit = self.button("edit", self.toggle_edit)
        self.edit.setCheckable(True)
        self.edit.setObjectName("edit")
        right.addWidget(self.edit)
        self.slider(right, "hand_size", "hand_size", 35, 180, "%")
        self.slider(right, "squish", "strength", 0, 25, "%")
        self.slider(right, "fps", "speed", 6, 30, "")
        reset_hand = self.button("reset_hand", self.reset_hand)
        reset_hand.setObjectName("quiet")
        right.addWidget(reset_hand, alignment=Qt.AlignLeft)
        right.addWidget(self.rule())
        self.disclosure = QToolButton()
        self.disclosure.setObjectName("disclosure")
        self.disclosure.setCheckable(True)
        self.disclosure.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.disclosure.setArrowType(Qt.RightArrow)
        self.bind(self.disclosure, "advanced")
        right.addWidget(self.disclosure)
        self.extra = QWidget()
        extra = QVBoxLayout(self.extra)
        extra.setContentsMargins(0, 0, 0, 0)
        extra.setSpacing(10)
        self.check(extra, "flip", "flip")
        self.check(extra, "pixel_art", "pixel")
        extra.addWidget(self.label("mode"))
        self.mode = QComboBox()
        self.mode.addItem("", "desktop")
        self.mode.addItem("", "top")
        self.mode.setCurrentIndex(1 if self.cfg["mode"] == "top" else 0)
        self.mode.currentIndexChanged.connect(lambda _: self.change("mode", self.mode.currentData()))
        extra.addWidget(self.mode)
        self.check(extra, "hide_fullscreen", "fullscreen")
        self.check(extra, "autostart", "startup")
        extra.addWidget(self.label("screen"))
        self.screen = QComboBox()
        self.populate_screens()
        self.screen.currentIndexChanged.connect(self.select_screen)
        extra.addWidget(self.screen)
        extra.addWidget(self.label("language"))
        self.language = QComboBox()
        self.language.addItem("Русский", "ru")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(self.cfg["language"] == "en")
        self.language.currentIndexChanged.connect(self.switch_language)
        extra.addWidget(self.language)
        extra.addWidget(self.label("original", "muted"))
        self.extra.hide()
        self.disclosure.toggled.connect(self.expand)
        right.addWidget(self.extra)
        right.addStretch()
        scroll.setWidget(content)
        columns.addWidget(scroll, 1)
        root.addLayout(columns, 1)

        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        self.notice.hide()
        root.addWidget(self.notice)
        footer = QHBoxLayout()
        move = self.button("move", lambda: self.move_requested.emit())
        footer.addWidget(move)
        footer.addStretch()
        footer.addWidget(self.button("cancel", self.reject))
        done = self.button("save", self.accept)
        done.setObjectName("primary")
        done.setDefault(True)
        footer.addWidget(done)
        root.addLayout(footer)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(70)
        self.debounce.timeout.connect(self.apply_preview)
        self.retranslate()
        self.update_character_name()

    def bind(self, widget, key):
        self.bindings.append((widget, key))
        widget.setText(tr(key, self.cfg["language"]))
        return widget

    def label(self, key, name=""):
        widget = QLabel()
        if name:
            widget.setObjectName(name)
        widget.setWordWrap(True)
        return self.bind(widget, key)

    def button(self, key, callback):
        widget = QPushButton()
        widget.clicked.connect(callback)
        return self.bind(widget, key)

    def rule(self):
        widget = QFrame()
        widget.setObjectName("rule")
        widget.setFixedHeight(2)
        return widget

    def slider(self, layout, key, title, low, high, suffix):
        group = QVBoxLayout()
        group.setSpacing(0)
        row = QHBoxLayout()
        label = self.label(title)
        row.addWidget(label)
        row.addStretch()
        value = QLabel(str(self.cfg[key]) + suffix)
        value.setObjectName("value")
        row.addWidget(value)
        group.addLayout(row)
        slider = SoftSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.setValue(self.cfg[key])
        slider.setAccessibleName(tr(title, self.cfg["language"]))
        slider.valueChanged.connect(lambda v: (value.setText(str(v) + suffix), self.change(key, v)))
        group.addWidget(slider)
        layout.addLayout(group)
        self.sliders[key] = (slider, value, suffix, title)

    def check(self, layout, key, title):
        check = QCheckBox()
        self.bind(check, title)
        check.setChecked(self.cfg[key])
        check.toggled.connect(lambda v: self.change(key, v))
        layout.addWidget(check)

    def change(self, key, value):
        self.cfg[key] = value
        self.preview.update()
        self.preview.timer.setInterval(round(1000 / self.cfg["fps"]))
        self.debounce.start()

    def apply_preview(self):
        self.on_preview(self.renderer, dict(self.cfg))

    def set_background(self, light):
        self.preview.light = light
        self.preview.update()

    def expand(self, expanded):
        self.extra.setVisible(expanded)
        self.disclosure.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

    def switch_language(self):
        self.cfg["language"] = self.language.currentData()
        self.retranslate()
        self.debounce.start()

    def retranslate(self):
        lang = self.cfg["language"]
        for widget, key in self.bindings:
            widget.setText(tr(key, lang))
        self.mode.setItemText(0, tr("mode_desktop", lang))
        self.mode.setItemText(1, tr("mode_top", lang))
        self.hint.setText(tr("edit_hint" if self.preview.editing else "hover", lang))
        self.edit.setText(tr("edit_done" if self.preview.editing else "edit", lang))
        for slider, value, suffix, title in self.sliders.values():
            slider.setAccessibleName(tr(title, lang))
        self.update_notice()

    def toggle_edit(self, checked):
        self.preview.editing = checked
        self.preview.setCursor(Qt.CrossCursor if checked else Qt.ArrowCursor)
        self.preview.update()
        self.retranslate()

    def move_hand(self, x, y):
        self.cfg.update(hand_x=x, hand_y=y)
        self.debounce.start()

    def reset_hand(self):
        for key in ("hand_x", "hand_y", "hand_size", "squish", "fps"):
            self.cfg[key] = DEFAULTS[key]
            if key in self.sliders:
                self.sliders[key][0].setValue(self.cfg[key])
        self.preview.update()
        self.debounce.start()

    def choose_png(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("choose", self.cfg["language"]), "", "PNG (*.png)")
        if path:
            self.import_png(path)

    def import_png(self, path):
        try:
            name, title = self.store.import_png(Path(path))
        except ValueError as exc:
            self.error(str(exc))
            return
        except OSError:
            self.error("write")
            return
        self.cfg.update(character=name, character_name=title, hand_x=DEFAULTS["hand_x"], hand_y=DEFAULTS["hand_y"])
        self.reload_character()

    def default_character(self):
        self.cfg.update(character="", character_name="Rufus", hand_x=DEFAULTS["hand_x"], hand_y=DEFAULTS["hand_y"])
        self.reload_character()

    def reload_character(self):
        if self.store.warning == "character":
            self.store.warning = ""
        self.renderer = Renderer(self.store.image(self.cfg, self.assets / "rufus.png"), self.assets / "hand.png")
        self.preview.renderer = self.renderer
        self.preview.update()
        self.update_character_name()
        self.update_notice()
        self.debounce.start()

    def update_character_name(self):
        self.character_name.setText(self.cfg["character_name"])

    def update_notice(self):
        if not hasattr(self, "notice"):
            return
        key = ""
        if self.store.warning:
            key = "missing" if self.store.warning == "character" else "recovered"
        # Fully opaque images are supported; make the visible background clear.
        if self.renderer.opaque:
            key = "opaque"
        self.notice.setVisible(bool(key))
        self.notice.setText(tr(key, self.cfg["language"]) if key else "")

    def populate_screens(self):
        self.screen.blockSignals(True)
        self.screen.clear()
        for index, screen in enumerate(QGuiApplication.screens()):
            width = round(screen.size().width() * screen.devicePixelRatio())
            height = round(screen.size().height() * screen.devicePixelRatio())
            self.screen.addItem(f"{index + 1} · {width} × {height}", screen.name())
        current = self.screen.findData(self.cfg["screen"])
        self.screen.setCurrentIndex(max(0, current))
        self.screen.blockSignals(False)

    def select_screen(self):
        self.cfg.update(screen=self.screen.currentData() or "", x=None, y=None)
        self.debounce.start()

    def error(self, key):
        QMessageBox.warning(self, tr("error", self.cfg["language"]), tr(key, self.cfg["language"]))

    def accept(self):
        self.debounce.stop()
        if self.on_commit(dict(self.cfg), self.renderer):
            super().accept()

    def reject(self):
        self.debounce.stop()
        super().reject()

    def dragEnterEvent(self, event):
        self.preview.dragEnterEvent(event)

    def dropEvent(self, event):
        self.preview.dropEvent(event)


class MoveDialog(QDialog):
    def __init__(self, language, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PetYourPet · " + tr("moving", language))
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 17, 22, 18)
        layout.addWidget(QLabel(tr("move_hint", language)))
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton(tr("cancel", language))
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        done = QPushButton(tr("save", language))
        done.setObjectName("primary")
        done.setDefault(True)
        done.clicked.connect(self.accept)
        row.addWidget(done)
        layout.addLayout(row)


class PlacementWindow(QWidget):
    """Opaque input surface kept separate from the click-through pet window.

    This window never receives the pet's transparent-input flags or attributes.
    """
    placed = Signal()
    cancelled = Signal()

    def __init__(self, pixmap):
        super().__init__()
        self.setWindowTitle("PetYourPet placement")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.pixmap = pixmap
        self.setFixedSize(pixmap.deviceIndependentSize().toSize())
        self.setCursor(Qt.SizeAllCursor)
        self.drag_offset = None
        self.completed = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#303c2d"))
        painter.drawPixmap(0, 0, self.pixmap)
        painter.setPen(QPen(QColor("#bdd6a5"), 2, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.grabMouse()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_offset is not None:
            self.releaseMouse()
        self.drag_offset = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.placed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.placed.emit()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if not self.completed:
            self.cancelled.emit()
        event.accept()
