# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis([str(root / 'run.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root / 'assets'), 'assets'), (str(root / 'LICENSES'), 'LICENSES'),
           (str(root / 'LICENSE'), '.'), (str(root / 'THIRD_PARTY.md'), '.')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'PySide6.QtQml', 'PySide6.QtQuick',
              'PySide6.QtTest', 'PySide6.QtSql', 'PySide6.QtOpenGL'],
    noarchive=False)
# The Qt Windows wheel uses the operating system's ICU shims. PyInstaller can
# otherwise collect an incompatible ICU DLL from unrelated tools on PATH.
system_icu = {'icuuc.dll', 'icuin.dll', 'icu.dll'}
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in system_icu]
pyz = PYZ(a.pure)
options = dict(debug=False, bootloader_ignore_signals=False, strip=False,
    upx=False, console=False, disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'icon.ico'), version=str(root / 'version_info.txt'),
    uac_admin=False)
portable_exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
    name='PetYourPet', contents_directory='_internal', **options)
portable = COLLECT(portable_exe, a.binaries, a.datas, strip=False, upx=False,
    name='PetYourPet-portable')
standalone = EXE(pyz, a.scripts, a.binaries, a.datas, [],
    name='PetYourPet-standalone', **options)
