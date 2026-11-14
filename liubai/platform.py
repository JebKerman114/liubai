"""Platform-specific launch commands, fonts and login startup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_ID = "io.github.JebKerman114.Liubai"
ROOT = Path(__file__).resolve().parent.parent


def startup_command() -> list[str]:
    if os.environ.get("APPIMAGE"):
        return [os.environ["APPIMAGE"]]
    if os.environ.get("FLATPAK_ID"):
        return ["flatpak", "run", os.environ["FLATPAK_ID"]]
    if os.environ.get("SNAP"):
        return ["snap", "run", "liubai"]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(ROOT / "main.py")]


def autostart_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart/liubai.desktop"


def autostart_enabled() -> bool:
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.QueryValueEx(key, "Liubai")
            return True
        except FileNotFoundError:
            return False
    return autostart_path().exists()


def desktop_quote(value: str) -> str:
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, "\\" + char)
    return '"' + value.replace("%", "%%") + '"'


def set_autostart(enabled: bool) -> None:
    command = startup_command() + ["--background"]
    if sys.platform == "win32":
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            if enabled:
                winreg.SetValueEx(key, "Liubai", 0, winreg.REG_SZ, subprocess.list2cmdline(command))
            else:
                try:
                    winreg.DeleteValue(key, "Liubai")
                except FileNotFoundError:
                    pass
        return
    path = autostart_path()
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        executable = " ".join(desktop_quote(arg) for arg in command)
        path.write_text(f"[Desktop Entry]\nType=Application\nName=留白\nExec={executable}\nIcon=liubai\nTerminal=false\nX-KDE-autostart-after=panel\n", encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def ui_font() -> str:
    from PySide6.QtGui import QFontDatabase
    available = set(QFontDatabase.families())
    for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC", "WenQuanYi Micro Hei", "Segoe UI", "DejaVu Sans"):
        if name in available:
            return name
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
