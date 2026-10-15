"""Build single-file and replaceable-DLL portable distributions, then source ZIP."""
from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from petyourpet import __version__


def write_runtime_licenses():
    destination = ROOT / "LICENSES" / "runtime"
    destination.mkdir(parents=True, exist_ok=True)
    # The compact checked-in Qt/font notices are retained without optional license alternatives.
    for location in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"):
        if location.exists():
            shutil.copy2(location, destination / "Python-LICENSE.txt")
            break
    versions = {name: importlib.metadata.version(name) for name in
                ("PySide6-Essentials", "shiboken6", "PyInstaller", "pyinstaller-hooks-contrib")}
    versions["Python"] = sys.version.split()[0]
    (destination / "VERSIONS.txt").write_text("\n".join(f"{name}=={version}" for name, version in versions.items()) + "\n", encoding="utf-8")


def add_tree(archive, directory, prefix):
    for file in sorted(directory.rglob("*")):
        if file.is_file() and "__pycache__" not in file.parts and file.suffix not in (".pyc", ".pyo"):
            archive.write(file, str(Path(prefix) / file.relative_to(directory)))


def main():
    if sys.platform != "win32":
        raise SystemExit("Build on Windows x64.")
    for path in ("assets/rufus.png", "assets/hand.png", "assets/fonts/PressStart2P-Regular.ttf",
                 "assets/fonts/IBMPlexMono-Regular.ttf", "LICENSES/qtbase/LICENSES/LGPL-3.0-only.txt"):
        if not (ROOT / path).exists():
            raise SystemExit("Missing checked-in resource: " + path)
    write_runtime_licenses()
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(ROOT / "PetYourPet.spec")], cwd=ROOT, check=True)
    package()
    subprocess.run([sys.executable, str(ROOT / "tools/check_release.py")], cwd=ROOT, check=True)


def package():
    """Refresh archives after documentation changes without rebuilding binaries."""
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "dist/PetYourPet-standalone.exe", release / "PetYourPet.exe")
    portable = ROOT / "dist/PetYourPet-portable"
    for name in ("README.md", "LICENSE", "THIRD_PARTY.md", "CHANGELOG.md"):
        shutil.copy2(ROOT / name, portable / name)
    shutil.copytree(ROOT / "LICENSES", portable / "LICENSES", dirs_exist_ok=True)
    runtime_zip = release / f"PetYourPet-{__version__}-win-x64.zip"
    with zipfile.ZipFile(runtime_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        add_tree(archive, portable, "PetYourPet")
    source_zip = release / f"PetYourPet-{__version__}-source.zip"
    prefix = "PetYourPet"
    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in ("petyourpet", "assets", "LICENSES", "tools", "tests", ".github", "docs"):
            directory = ROOT / name
            if directory.exists():
                add_tree(archive, directory, str(Path(prefix) / name))
        for name in ("run.py", "requirements.txt", "requirements-build.txt", "requirements-build-lock.txt",
                     ".gitignore", "README.md", "LICENSE", "THIRD_PARTY.md", "CHANGELOG.md",
                     "PUBLISHING.md", "PetYourPet.spec", "version_info.txt"):
            file = ROOT / name
            if file.exists():
                archive.write(file, str(Path(prefix) / name))
    sums = []
    notices_zip = release / "PetYourPet-notices.zip"
    with zipfile.ZipFile(notices_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        add_tree(archive, ROOT / "LICENSES", "LICENSES")
        archive.write(ROOT / "THIRD_PARTY.md", "THIRD_PARTY.md")
        archive.write(ROOT / "LICENSE", "LICENSE")
    for file in (release / "PetYourPet.exe", runtime_zip, source_zip, notices_zip):
        sums.append(hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.name)
        print(file.name, round(file.stat().st_size / 1024 / 1024, 2), "MB")
    (release / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
