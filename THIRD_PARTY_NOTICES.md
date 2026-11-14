# Third-party components

Liubai is licensed under the MIT License. Bundled components retain their own licenses.

| Component | License | Source |
| --- | --- | --- |
| Python | Python Software Foundation License | https://www.python.org/downloads/source/ |
| PySide6, Shiboken6 and Qt | LGPL-3.0 / GPL-3.0 / component-specific licenses | https://code.qt.io/pyside/pyside-setup.git/ and https://code.qt.io/qt/ |
| PyInstaller bootloader | GPL-2.0-or-later with bootloader exception | https://github.com/pyinstaller/pyinstaller |

The distribution contains the available upstream license texts under `licenses/`.
Qt and PySide6 are dynamically bundled as separate files. The portable distribution
can be extracted and its libraries replaced with compatible builds. Exact component
versions are recorded in `build-info.json`; the build scripts and application source
are available at https://github.com/JebKerman114/liubai.

No commercial Qt license is implied. See the upstream license texts for the terms
applicable to each bundled library and plugin.
