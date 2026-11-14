"""Use Fcitx's IBus frontend when bundled Qt has no Fcitx input plugin.

See https://fcitx-im.org/wiki/Setup_Fcitx_5#Qt
Only this process is affected; desktop input settings remain untouched.
"""

import os
from pathlib import Path

from PySide6.QtCore import QLibraryInfo


def configure_input_method():
    requested = os.environ.get("QT_IM_MODULE", "")
    if requested not in ("fcitx", "fcitx5"):
        return
    plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)) / "platforminputcontexts"
    if not any(plugins.glob("*fcitx*.so")) and (plugins / "libibusplatforminputcontextplugin.so").exists():
        os.environ["QT_IM_MODULE"] = "ibus"
