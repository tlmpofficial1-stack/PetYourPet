"""Source and PyInstaller entry point, including startup diagnostics."""
import os
from pathlib import Path
import sys
import traceback


def launch():
    try:
        from petyourpet.app import main
        return main()
    except Exception:
        details = traceback.format_exc()
        try:
            if "--data-dir" in sys.argv:
                root = Path(sys.argv[sys.argv.index("--data-dir") + 1])
            else:
                root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PetYourPet" / "PetYourPet"
            root.mkdir(parents=True, exist_ok=True)
            (root / "startup-error.log").write_text(details, encoding="utf-8")
        except OSError:
            pass
        if "--smoke-output" not in sys.argv:
            try:
                from PySide6.QtWidgets import QApplication, QMessageBox
                app = QApplication.instance() or QApplication([])
                QMessageBox.critical(None, "PetYourPet", "Could not start PetYourPet.\n\n" + details)
            except Exception:
                pass
        return 1

if __name__ == "__main__":
    raise SystemExit(launch())
