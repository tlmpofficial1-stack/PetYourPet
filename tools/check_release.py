"""Check the actual EXEs, single-instance behavior, and publication archives."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / ".qa" / "release-check"


def main():
    QA.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(key, None)
    # Verify packaged startup and rendering without opening desktop windows.
    # Native Windows input styles are covered separately by the test suite.
    environment["QT_QPA_PLATFORM"] = "offscreen"
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    results = {}
    for name, executable in (("single-file", ROOT / "release/PetYourPet.exe"),
                             ("portable", ROOT / "dist/PetYourPet-portable/PetYourPet.exe")):
        data = QA / name
        report = QA / (name + ".json")
        screenshot = QA / (name + ".png")
        if report.exists():
            report.unlink()
        subprocess.run([str(executable), "--test-mode", "--data-dir", str(data),
                        "--smoke-output", str(report), "--screenshot", str(screenshot)],
                       env=environment, startupinfo=startup, check=True, timeout=45)
        health = json.loads(report.read_text())
        assert health["frozen"] and health["character_loaded"] and health["hand_loaded"]
        assert health["frames"] == 10 and health["fonts_loaded"]
        assert health["native_click_through"] in (True, None)
        results[name] = health
        print(name, "EXE passed", flush=True)

    # Two launches share one lock and notify the original process; neither
    # a second pet nor a second independent settings store should be created.
    data = QA / "instance-test"
    data.mkdir(exist_ok=True)
    (data / "settings.json").write_text("{}", encoding="utf-8")
    executable = str(ROOT / "release/PetYourPet.exe")
    first = subprocess.Popen([executable, "--test-mode", "--background", "--data-dir", str(data),
                              "--quit-after-ms", "6500"], env=environment, startupinfo=startup)
    lock = data / "instance.lock"
    deadline = time.monotonic() + 8
    while not lock.exists() and time.monotonic() < deadline:
        time.sleep(.1)
    assert lock.exists(), "First instance never acquired its lock"
    owner = lock.read_text().splitlines()[0]
    unexpected = QA / "unexpected-second.json"
    if unexpected.exists():
        unexpected.unlink()
    subprocess.run([executable, "--test-mode", "--data-dir", str(data),
                    "--smoke-output", str(unexpected)], env=environment,
                   startupinfo=startup, check=True, timeout=10)
    assert not unexpected.exists(), "Second launch created a separate application"
    assert lock.read_text().splitlines()[0] == owner
    assert first.poll() is None, "First instance unexpectedly exited"
    assert first.wait(timeout=15) == 0
    results["single_instance"] = True

    release = ROOT / "release"
    for line in (release / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((release / name).read_bytes()).hexdigest() == digest
    for archive_path in release.glob("*.zip"):
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert not any(".qa/" in name or "__pycache__/" in name or "characters/" in name for name in names)
            if "source" in archive_path.name:
                assert "PetYourPet/assets/fonts/PressStart2P-Regular.ttf" in names
                assert "PetYourPet/LICENSES/qtbase/LICENSES/LGPL-3.0-only.txt" in names
                for name in names:
                    if Path(name).suffix in (".py", ".md", ".txt", ".yml"):
                        assert str(Path.home()).encode() not in archive.read(name), "Private machine path in source archive"
    results["archives_and_hashes"] = True
    (QA / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Single instance, archive integrity, bundled resources and SHA-256 passed")


if __name__ == "__main__":
    main()
