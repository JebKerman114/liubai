# PyInstaller spec. Build on the target OS and architecture.
import os
from pathlib import Path

root = Path(SPECPATH).parent
windows = os.name == "nt"
a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=["PySide6.QtDBus"] if not windows else [],
    hookspath=[],
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="liubai",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "assets/liubai.ico") if windows else None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="liubai")
