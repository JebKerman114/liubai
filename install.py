#!/usr/bin/env python3
"""Install a self-contained source copy and user-level desktop launcher."""

import os
import shutil
import sys
from pathlib import Path


def desktop_quote(value):
    for character in ('\\', '"', '`', '$'):
        value = value.replace(character, "\\" + character)
    return '"' + value.replace("%", "%%") + '"'


def main():
    try:
        import PySide6  # noqa: F401
    except ImportError:
        sys.exit("请先安装依赖：python3 -m pip install -r requirements.txt")
    source = Path(__file__).resolve().parent
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    target = data_home / "liubai-app"
    target.mkdir(parents=True, exist_ok=True)
    if source != target:
        for name in ("main.py", "launch.sh", "requirements.txt", "README.md"):
            shutil.copy2(source / name, target / name)
        for name in ("liubai", "assets"):
            shutil.copytree(source / name, target / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    (target / "launch.sh").chmod(0o755)
    # Pin the interpreter used for installation, including a virtualenv if present.
    launcher = target / "run"
    import shlex
    launcher.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(target / "main.py")) + ' "$@"\n', encoding="utf-8")
    launcher.chmod(0o755)
    applications = data_home / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    icon_dir = data_home / "icons/hicolor/scalable/apps"
    icon_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target / "assets/liubai.svg", icon_dir / "liubai.svg")
    (applications / "liubai.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=留白\nGenericName=待办与便签\n"
        "Comment=桌面待办与便签\n"
        f"Exec={desktop_quote(str(launcher))}\nIcon=liubai\nTerminal=false\n"
        "Categories=Utility;\nKeywords=todo;notes;sticky;待办;便签;留白;\n"
        "StartupNotify=true\nStartupWMClass=liubai\n", encoding="utf-8")
    print(f"已安装：{target}\n在应用菜单搜索「留白」即可打开。\n启动命令：{launcher}")


if __name__ == "__main__":
    main()
