#!/usr/bin/env python3
"""Package an existing native bundle for Linux. No root access required."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import yaml
from build import ROOT, architecture, checksums
import sys
sys.path.insert(0, str(ROOT))
from liubai import __version__
from liubai.platform import APP_ID

RELEASE = ROOT / "release"
BUNDLE = ROOT / "dist/liubai"
ARCH = architecture()
DEB_ARCH = {"x86_64": "amd64", "aarch64": "arm64"}[ARCH]
NAME = f"liubai-{__version__}-linux-{ARCH}"
TOOLS = ROOT / ".tools"
APPIMAGE_HASH = {
    "x86_64": "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0",
    "aarch64": "f0837e7448a0c1e4e650a93bb3e85802546e60654ef287576f46c71c126a9158",
}


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    run("curl", "--fail", "--location", "--retry", "3", "--connect-timeout", "20", "--max-time", "300", "--output", path, url)


def nfpm():
    tool = TOOLS / "nfpm"
    if tool.exists():
        return tool
    arch = "x86_64" if ARCH == "x86_64" else "arm64"
    archive = TOOLS / f"nfpm_2.49.0_Linux_{arch}.tar.gz"
    base = "https://github.com/goreleaser/nfpm/releases/download/v2.49.0/"
    download(base + archive.name, archive)
    manifest = TOOLS / "nfpm-checksums.txt"
    download(base + "checksums.txt", manifest)
    expected = next(line.split()[0] for line in manifest.read_text().splitlines() if line.endswith(archive.name))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected, "nFPM checksum mismatch"
    with tarfile.open(archive) as stream:
        tool.write_bytes(stream.extractfile("nfpm").read())
    tool.chmod(0o755)
    return tool


def native_packages():
    contents = []
    for source in sorted(BUNDLE.rglob("*")):
        destination = "/opt/liubai/" + source.relative_to(BUNDLE).as_posix()
        if source.is_symlink():
            contents.append({"src": os.readlink(source), "dst": destination, "type": "symlink"})
        elif source.is_file():
            contents.append({"src": str(source), "dst": destination,
                             "file_info": {"mode": source.stat().st_mode & 0o777}})
    contents.extend([
        {"src": "/opt/liubai/liubai", "dst": "/usr/bin/liubai", "type": "symlink"},
        {"src": str(ROOT / "packaging/liubai.desktop"), "dst": "/usr/share/applications/liubai.desktop"},
        {"src": str(ROOT / "assets/liubai.svg"), "dst": "/usr/share/icons/hicolor/scalable/apps/liubai.svg"},
        {"src": str(ROOT / f"packaging/{APP_ID}.metainfo.xml"), "dst": f"/usr/share/metainfo/{APP_ID}.metainfo.xml"},
    ])
    dependencies = {
        "deb": ["libc6 (>= 2.39)", "libgl1", "libegl1", "libxcb-cursor0", "libxkbcommon0", "libdbus-1-3"],
        "rpm": ["glibc >= 2.39", "libGL.so.1()(64bit)", "libEGL.so.1()(64bit)", "libxcb-cursor.so.0()(64bit)", "libxkbcommon.so.0()(64bit)"],
        "archlinux": ["glibc>=2.39", "libglvnd", "xcb-util-cursor", "libxkbcommon", "dbus"],
    }
    for packager, extension in [("deb", "deb"), ("rpm", "rpm"), ("archlinux", "pkg.tar.zst")]:
        config = {"name": "liubai", "arch": DEB_ARCH, "platform": "linux", "version": __version__,
                  "maintainer": "Liubai contributors <204438646+JebKerman114@users.noreply.github.com>",
                  "description": "Desktop tasks and sticky notes with always-on-top support.",
                  "homepage": "https://github.com/JebKerman114/liubai", "license": "MIT",
                  "section": "utils", "priority": "optional", "contents": contents,
                  "depends": dependencies[packager]}
        path = ROOT / f"build/nfpm-{packager}.yaml"
        path.parent.mkdir(exist_ok=True)
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        run(nfpm(), "package", "--config", path, "--packager", packager, "--target", RELEASE / f"{NAME}.{extension}")


def appimage():
    appdir = ROOT / "build/Liubai.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)
    shutil.copytree(BUNDLE, appdir / "usr/lib/liubai", symlinks=True)
    shutil.copy2(ROOT / "packaging/liubai.desktop", appdir / "liubai.desktop")
    shutil.copy2(ROOT / "assets/liubai.svg", appdir / "liubai.svg")
    shutil.copy2(ROOT / "assets/liubai.svg", appdir / ".DirIcon")
    launcher = appdir / "AppRun"
    launcher.write_text('#!/bin/sh\napp_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$app_dir/usr/lib/liubai/liubai" "$@"\n', encoding="utf-8")
    launcher.chmod(0o755)
    tool = TOOLS / f"appimagetool-{ARCH}.AppImage"
    if not tool.exists():
        download(f"https://github.com/AppImage/appimagetool/releases/download/1.9.1/{tool.name}", tool)
    assert hashlib.sha256(tool.read_bytes()).hexdigest() == APPIMAGE_HASH[ARCH], "appimagetool checksum mismatch"
    tool.chmod(0o755)
    run(tool, "--appimage-extract-and-run", "--no-appstream", appdir, RELEASE / f"{NAME}.AppImage", env=dict(os.environ, ARCH=ARCH))


def flatpak():
    stage = ROOT / "build/flatpak"
    if stage.exists():
        shutil.rmtree(stage)
    files = stage / "files"
    shutil.copytree(BUNDLE, files / "lib/liubai", symlinks=True)
    binary = files / "bin/liubai"
    binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nexport QT_QPA_PLATFORM=xcb\nexec /app/lib/liubai/liubai "$@"\n', encoding="utf-8")
    binary.chmod(0o755)
    for source, destination in [
        (ROOT / "packaging/liubai.desktop", files / f"share/applications/{APP_ID}.desktop"),
        (ROOT / "assets/liubai.svg", files / f"share/icons/hicolor/scalable/apps/{APP_ID}.svg"),
        (ROOT / f"packaging/{APP_ID}.metainfo.xml", files / f"share/metainfo/{APP_ID}.metainfo.xml"),
    ]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    desktop = files / f"share/applications/{APP_ID}.desktop"
    desktop.write_text(desktop.read_text().replace("Icon=liubai", f"Icon={APP_ID}"), encoding="utf-8")
    (stage / "metadata").write_text(
        f"[Application]\nname={APP_ID}\nruntime=org.kde.Platform/{ARCH}/6.10\ncommand=liubai\n"
        "\n[Context]\nshared=ipc;\nsockets=x11;\ndevices=dri;\n"
        "\n[Session Bus Policy]\norg.kde.StatusNotifierWatcher=talk\norg.freedesktop.IBus=talk\n", encoding="utf-8")
    repository = ROOT / "build/flatpak-repo"
    run("flatpak", "build-finish", stage)
    run("flatpak", "build-export", "--disable-sandbox", repository, stage, "stable")
    run("flatpak", "build-bundle", f"--arch={ARCH}", "--runtime-repo=https://flathub.org/repo/flathub.flatpakrepo",
        repository, RELEASE / f"{NAME}.flatpak", APP_ID, "stable")


def snap():
    stage = ROOT / "build/snap"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(BUNDLE, stage / "app", symlinks=True)
    (stage / "meta/gui").mkdir(parents=True)
    shutil.copy2(ROOT / "assets/liubai.png", stage / "meta/gui/icon.png")
    shutil.copy2(ROOT / "packaging/liubai.desktop", stage / "meta/gui/liubai.desktop")
    metadata = {"name": "liubai", "version": __version__, "summary": "Desktop tasks and sticky notes",
                "description": "Local desktop tasks and notes with automatic saving and an always-on-top window.",
                "base": "core24", "architectures": [DEB_ARCH], "confinement": "classic", "grade": "stable",
                "apps": {"liubai": {"command": "app/liubai", "environment": {"QT_QPA_PLATFORM": "xcb"}}}}
    (stage / "meta/snap.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    run("mksquashfs", stage, RELEASE / f"{NAME}.snap", "-noappend", "-comp", "xz", "-all-root")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--formats", nargs="+", choices=["native", "appimage", "flatpak", "snap"], default=["native", "appimage", "flatpak", "snap"])
    args = parser.parse_args()
    if not BUNDLE.exists():
        raise SystemExit("Run scripts/build.py first.")
    RELEASE.mkdir(exist_ok=True)
    for kind in args.formats:
        {"native": native_packages, "appimage": appimage, "flatpak": flatpak, "snap": snap}[kind]()
    checksums(RELEASE)


if __name__ == "__main__":
    main()
