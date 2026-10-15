"""Independent, bottom-anchored petting animation with an editable contact point."""
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

FRAME_COUNT = 10


class Renderer:
    def __init__(self, image: QImage, hand: Path):
        if image.isNull():
            raise ValueError("Empty character image")
        self.image = image
        rgba = image.convertToFormat(QImage.Format_ARGB32)
        alpha = bytes(rgba.constBits())[3::4]
        self.opaque = alpha.count(b"\xff") == len(alpha)
        self.hand = QImage(str(hand))
        if self.hand.isNull() or self.hand.width() != self.hand.height() * 5:
            raise ValueError("Invalid bundled hand sprite")

    def geometry(self, cfg: dict, height: float | None = None):
        height = height or cfg["height"]
        width = height * self.image.width() / self.image.height()
        # Both portrait and panoramic PNGs remain manageable desktop windows.
        if width > 600:
            height *= 600 / width
            width = 600
        body = QRectF(0, 0, width, height)
        hand_side = max(48, width) * cfg["hand_size"] / 100
        hand_side = min(hand_side, 620)
        anchor = QPointF(width * cfg["hand_x"], height * cfg["hand_y"])
        hand = QRectF(anchor.x() - hand_side * .65, anchor.y() - hand_side * .58,
                      hand_side, hand_side)
        extents = body.adjusted(-width * .13, -4, width * .13, 4).united(hand)
        for i in range(FRAME_COUNT):
            compression = math.sin(math.pi * i / FRAME_COUNT) ** 2 * cfg["squish"] / 100
            contact = (.58, .74, .88, .74, .58)[i // 2]
            extents = extents.united(hand.translated(0, height * compression * (1 - cfg["hand_y"]) - hand_side * (contact - .58)))
        extents = extents.adjusted(-10, -10, 10, 10)
        offset = -extents.topLeft()
        body.translate(offset)
        hand.translate(offset)
        return QSize(math.ceil(extents.width()), math.ceil(extents.height())), body, hand

    def draw(self, painter: QPainter, cfg: dict, frame: int | None, height: float | None = None):
        _, body, hand = self.geometry(cfg, height)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, not cfg["pixel_art"])
        strength = 0 if frame is None else math.sin(math.pi * (frame % FRAME_COUNT) / FRAME_COUNT) ** 2
        compression = strength * cfg["squish"] / 100
        width = body.width() * (1 + compression * .6)
        squashed = QRectF(body.center().x() - width / 2, body.top() + body.height() * compression,
                          width, body.height() * (1 - compression))
        painter.save()
        if cfg["flip"]:
            painter.translate(squashed.center().x() * 2, 0)
            painter.scale(-1, 1)
        painter.drawImage(squashed, self.image)
        painter.restore()
        if frame is not None:
            index = min(4, (frame % FRAME_COUNT) // 2)
            cell = self.hand.height()
            # The source hand contact changes between frames. Keep its bottom
            # fingers at the selected contact point as the body compresses.
            contact = (.58, .74, .88, .74, .58)[index]
            hand.translate(0, body.height() * compression * (1 - cfg["hand_y"]) - hand.height() * (contact - .58))
            painter.drawImage(hand, self.hand, QRectF(index * cell, 0, cell, cell))

    def pixmap(self, cfg: dict, frame: int | None, dpr: float = 1.0) -> QPixmap:
        size, _, _ = self.geometry(cfg)
        result = QPixmap(math.ceil(size.width() * dpr), math.ceil(size.height() * dpr))
        result.setDevicePixelRatio(dpr)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        self.draw(painter, cfg, frame)
        painter.end()
        return result

    def frames(self, cfg: dict, dpr: float = 1.0):
        return self.pixmap(cfg, None, dpr), [self.pixmap(cfg, i, dpr) for i in range(FRAME_COUNT)]
