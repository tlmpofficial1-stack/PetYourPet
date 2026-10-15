"""Create a Windows application icon from the owner-supplied Rufus PNG."""
from pathlib import Path
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBitmap, QIcon, QImage, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
app = QApplication(sys.argv[:1])
image = QImage(str(ROOT / "assets" / "rufus.png"))
assert not image.isNull()
# Qt's ICO writer includes one 256px image; Windows scales it for the tray.
icon = image.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
canvas = QImage(256, 256, QImage.Format_ARGB32)
canvas.fill(Qt.transparent)
painter = QPainter(canvas)
painter.drawImage((256 - icon.width()) // 2, (256 - icon.height()) // 2, icon)
painter.end()
assert canvas.save(str(ROOT / "assets" / "icon.ico"))
print("Generated Rufus application icon")
