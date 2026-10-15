"""Capture application-owned widgets for documentation; no screen automation."""
import argparse
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from petyourpet.app import assets_directory
from petyourpet.render import Renderer
from petyourpet.storage import DEFAULTS, Store
from petyourpet.ui import SettingsDialog

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--character", type=Path)
parser.add_argument("--language", choices=("ru", "en"), default="ru")
parser.add_argument("--advanced", action="store_true")
parser.add_argument("--hand", action="store_true")
parser.add_argument("--small", action="store_true")
args = parser.parse_args()
app = QApplication([])
assets = assets_directory()
for path in (assets / "fonts").glob("*.ttf"):
    QFontDatabase.addApplicationFont(str(path))
with tempfile.TemporaryDirectory() as data:
    store = Store(Path(data))
    cfg = dict(DEFAULTS, language=args.language)
    if args.character:
        cfg["character"], cfg["character_name"] = store.import_png(args.character)
    renderer = Renderer(store.image(cfg, assets / "rufus.png"), assets / "hand.png")
    dialog = SettingsDialog(store, cfg, renderer, assets, lambda *_: None, lambda *_: False)
    if args.small:
        dialog.resize(820, 610)
    if args.advanced:
        dialog.disclosure.setChecked(True)
    if args.hand:
        dialog.edit.click()
    dialog.show()
    app.processEvents()
    if args.advanced:
        from PySide6.QtWidgets import QScrollArea
        area = dialog.findChild(QScrollArea)
        area.ensureWidgetVisible(dialog.language)
        app.processEvents()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    assert dialog.grab().save(str(args.output))
    dialog.reject()
