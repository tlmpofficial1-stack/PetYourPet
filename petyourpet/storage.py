"""Validated settings and owned, normalized PNG imports. No GUI side effects."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QImage, QImageReader

DEFAULTS = {
    "version": 2, "character": "", "character_name": "Rufus",
    "height": 210, "hand_size": 100, "hand_x": 0.52, "hand_y": 0.06,
    "squish": 13, "fps": 16, "flip": False, "pixel_art": False,
    "mode": "desktop", "screen": "", "x": None, "y": None,
    "language": "en", "hide_fullscreen": True, "autostart": False,
}
LIMITS = {"height": (70, 500), "hand_size": (35, 180),
          "squish": (0, 25), "fps": (6, 30),
          "hand_x": (-0.25, 1.25), "hand_y": (-0.2, 0.65),
          "x": (-100000, 100000), "y": (-100000, 100000)}


def validate(raw: object) -> dict:
    cfg = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if key in LIMITS:
            if key in ("x", "y") and value is None:
                cfg[key] = None
            elif type(value) in (int, float) and math.isfinite(value):
                low, high = LIMITS[key]
                value = max(low, min(high, value))
                cfg[key] = float(value) if key.startswith("hand_") and key != "hand_size" else int(value)
        elif isinstance(default, bool):
            cfg[key] = value if type(value) is bool else default
        elif isinstance(default, str) and isinstance(value, str):
            cfg[key] = value[:1024]
    if cfg["language"] not in ("ru", "en"):
        cfg["language"] = "en"
    if cfg["mode"] not in ("desktop", "top", "hide"):
        cfg["mode"] = "desktop"
    # Early prototypes defaulted to Russian; switch those once on upgrade.
    if type(raw.get("version")) is not int or raw["version"] < 2:
        cfg["language"] = "en"
        if not cfg["character"]:
            cfg["character_name"] = "Rufus"
    cfg["version"] = 2
    # Configs only refer to files inside our own characters directory.
    name = cfg["character"]
    if name and (Path(name).name != name or not name.endswith(".png") or "/" in name or "\\" in name):
        cfg["character"] = ""
    return cfg


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root or Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        self.characters = self.root / "characters"
        self.root.mkdir(parents=True, exist_ok=True)
        self.characters.mkdir(exist_ok=True)
        self.path = self.root / "settings.json"
        self.warning = ""

    def load(self) -> dict:
        if not self.path.exists():
            return dict(DEFAULTS)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Expected a JSON object")
            return validate(raw)
        except (OSError, ValueError, UnicodeError):
            self.warning = "settings"
            # Preserve the damaged file before any later save replaces it.
            try:
                from datetime import datetime
                backup = self.root / ("settings-invalid-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
                backup.write_bytes(self.path.read_bytes())
            except OSError:
                pass
            return dict(DEFAULTS)

    def save(self, cfg: dict):
        payload = json.dumps(validate(cfg), indent=2, ensure_ascii=False).encode("utf-8")
        self._atomic(self.path, payload)

    @staticmethod
    def _atomic(path: Path, payload: bytes):
        fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def import_png(self, path: Path) -> tuple[str, str]:
        """Read before copying, trim transparent borders, retain an owned copy."""
        if path.suffix.lower() != ".png" or not path.is_file():
            raise ValueError("png")
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("large")
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        dimensions = reader.size()
        if (bytes(reader.format()).lower() != b"png" or not dimensions.isValid()):
            raise ValueError("png")
        if dimensions.width() > 8192 or dimensions.height() > 8192 or dimensions.width() * dimensions.height() > 16_000_000:
            raise ValueError("large")
        image = reader.read()
        if image.isNull():
            raise ValueError("png")
        # Let Qt scan the alpha mask natively instead of a Python pixel loop.
        from PySide6.QtGui import QBitmap, QRegion
        from PySide6.QtCore import Qt
        premultiplied = image.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        mask = premultiplied.createMaskFromColor(0, Qt.MaskInColor)
        bounds = QRegion(QBitmap.fromImage(mask)).boundingRect()
        if bounds.isEmpty():
            raise ValueError("empty")
        image = image.copy(bounds).convertToFormat(QImage.Format_ARGB32)
        # Large source art is normalized to a sensible working size once.
        if max(image.width(), image.height()) > 2048:
            image = image.scaled(2048, 2048, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        from PySide6.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise OSError("PNG encoding failed")
        payload = bytes(buffer.data())
        filename = hashlib.sha256(payload).hexdigest()[:24] + ".png"
        self._atomic(self.characters / filename, payload)
        return filename, path.stem[:80]

    def image(self, cfg: dict, default: Path) -> QImage:
        path = self.characters / cfg["character"] if cfg["character"] else default
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            if cfg["character"]:
                self.warning = "character"
            image = QImage(str(default))
        return image
