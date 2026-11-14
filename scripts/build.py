#!/usr/bin/env python3
"""Freeze the native app, include notices, and generate portable archives."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from liubai import __version__


def architecture():
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "x64" if os.name == "nt" else "x86_64"
    if machine in ("arm64", "aarch64"):
        return "arm64" if os.name == "nt" else "aarch64"
    raise SystemExit(f"Unsupported architecture: {machine}; supported: x64 and ARM64.")


def make_icons():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PIL import Image
    app = QGuiApplication.instance() or QGuiApplication([])
    renderer = QSvgRenderer(str(ROOT / "assets/liubai.svg"))
    target = QImage(256, 256, QImage.Format.Format_ARGB32)
    target.fill(0)
    painter = QPainter(target)
    renderer.render(painter)
    painter.end()
    target.save(str(ROOT / "assets/liubai.png"))
    image = Image.open(ROOT / "assets/liubai.png")
    image.save(ROOT / "assets/liubai.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def bundle_notices(bundle):
    for file in ("LICENSE", "THIRD_PARTY_NOTICES.md", "README.md"):
        shutil.copy2(ROOT / file, bundle / file)
    shutil.copytree(ROOT / "packaging/licenses", bundle / "licenses", dirs_exist_ok=True)
    for package in ("PySide6-Essentials", "shiboken6", "PyInstaller"):
        dist = importlib.metadata.distribution(package)
        for relative in dist.files or []:
            if "license" in str(relative).lower() or "copying" in str(relative).lower():
                source = Path(dist.locate_file(relative))
                if source.is_file():
                    target = bundle / "licenses" / package / str(relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    import sysconfig
    python_license = Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"
    if python_license.exists():
        target = bundle / "licenses/Python/LICENSE.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(python_license, target)
    info = {"application": __version__, "python": platform.python_version(),
            "platform": platform.system(), "architecture": architecture(),
            "PySide6-Essentials": importlib.metadata.version("PySide6-Essentials"),
            "PyInstaller": importlib.metadata.version("PyInstaller")}
    (bundle / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


def checksums(directory):
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    lines = [hashlib.file_digest(p.open("rb"), "sha256").hexdigest() + "  " + p.name for p in files]
    (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-freeze", action="store_true")
    parser.add_argument("--checksums-only", action="store_true")
    args = parser.parse_args()
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    if args.checksums_only:
        checksums(release)
        return
    make_icons()
    if not args.skip_freeze:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(ROOT / "packaging/liubai.spec")], cwd=ROOT, check=True)
    bundle = ROOT / "dist/liubai"
    bundle_notices(bundle)
    target = "windows" if os.name == "nt" else "linux"
    name = f"liubai-{__version__}-{target}-{architecture()}"
    if target == "windows":
        shutil.make_archive(str(release / f"{name}-portable"), "zip", root_dir=ROOT / "dist", base_dir="liubai")
    else:
        with tarfile.open(release / f"{name}.tar.gz", "w:gz") as archive:
            archive.add(bundle, arcname="liubai")
    checksums(release)
    print(f"Built {name} -> {release}")


if __name__ == "__main__":
    main()
