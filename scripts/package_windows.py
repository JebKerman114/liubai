#!/usr/bin/env python3
"""Create portable ZIP, Inno Setup EXE, MSI, and unsigned MSIX."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from build import ROOT, architecture, checksums
import sys
sys.path.insert(0, str(ROOT))
from liubai import __version__

BUNDLE = ROOT / "dist/liubai"
RELEASE = ROOT / "release"
WORK = ROOT / "build/windows-packages"
ARCH = architecture()
NAME = f"liubai-{__version__}-windows-{ARCH}"


def run(*args):
    subprocess.run([str(a) for a in args], check=True)


def inno_setup():
    compiler = shutil.which("ISCC.exe") or shutil.which("iscc")
    if not compiler:
        candidates = list(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).glob("Inno Setup */ISCC.exe"))
        if candidates:
            compiler = str(sorted(candidates)[-1])
    if not compiler:
        raise RuntimeError("Inno Setup is required. Install with: choco install innosetup -y")
    arch_expression = "arm64" if ARCH == "arm64" else "x64compatible"
    template = f"""[Setup]
AppId=Liubai.{ARCH}
AppName=留白
AppVersion={__version__}
AppPublisher=Liubai contributors
AppPublisherURL=https://github.com/JebKerman114/liubai
DefaultDirName={{localappdata}}\\Programs\\Liubai
DefaultGroupName=留白
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed={arch_expression}
ArchitecturesInstallIn64BitMode={arch_expression}
OutputDir={RELEASE}
OutputBaseFilename={NAME}-setup
SetupIconFile={ROOT / 'assets/liubai.ico'}
UninstallDisplayIcon={{app}}\\liubai.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Files]
Source: "{BUNDLE}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\留白"; Filename: "{{app}}\\liubai.exe"

[Run]
Filename: "{{app}}\\liubai.exe"; Description: "打开留白"; Flags: nowait postinstall skipifsilent
"""
    script = WORK / "installer.iss"
    script.write_text(template, encoding="utf-8-sig")
    run(compiler, script)


def msi():
    namespace = "http://wixtoolset.org/schemas/v4/wxs"
    ET.register_namespace("", namespace)

    def element(parent, tag, **attrs):
        return ET.SubElement(parent, "{" + namespace + "}" + tag, attrs)

    root = ET.Element("{" + namespace + "}Wix")
    package = element(root, "Package", Name="Liubai", Manufacturer="Liubai contributors",
                      Version=__version__, Language="1033", Scope="perMachine",
                      UpgradeCode=str(uuid5(NAMESPACE_URL, f"https://github.com/JebKerman114/liubai/{ARCH}")).upper())
    element(package, "MajorUpgrade", DowngradeErrorMessage="A newer version of Liubai is already installed.")
    element(package, "MediaTemplate", EmbedCab="yes", CompressionLevel="high")
    element(package, "Icon", Id="AppIcon", SourceFile=str(ROOT / "assets/liubai.ico"))
    element(package, "Property", Id="ARPPRODUCTICON", Value="AppIcon")
    program_files = element(package, "StandardDirectory", Id="ProgramFiles64Folder")
    folder = element(program_files, "Directory", Id="INSTALLFOLDER", Name="Liubai")
    element(package, "StandardDirectory", Id="ProgramMenuFolder")
    feature = element(package, "Feature", Id="Main", Title="Liubai", Level="1")
    directories = {Path("."): (folder, "INSTALLFOLDER")}

    def identifier(path):
        return hashlib.sha256(path.as_posix().encode()).hexdigest()[:24]

    for source in sorted(BUNDLE.rglob("*")):
        relative = source.relative_to(BUNDLE)
        if source.is_dir():
            parent = directories[relative.parent][0]
            directory_id = "d" + identifier(relative)
            directories[relative] = (element(parent, "Directory", Id=directory_id, Name=source.name), directory_id)
        else:
            parent = directories[relative.parent][0]
            component_id = "c" + identifier(relative)
            component = element(parent, "Component", Id=component_id, Guid="*", Bitness="always64")
            file = element(component, "File", Id="f" + identifier(relative), Source=str(source), KeyPath="yes")
            if relative.as_posix() == "liubai.exe":
                element(file, "Shortcut", Id="StartMenu", Directory="ProgramMenuFolder", Name="Liubai", Advertise="yes", Icon="AppIcon", WorkingDirectory="INSTALLFOLDER")
            element(feature, "ComponentRef", Id=component_id)
    script = WORK / "installer.wxs"
    ET.ElementTree(root).write(script, encoding="utf-8", xml_declaration=True)
    run("wix", "build", "-arch", ARCH, "-o", RELEASE / f"{NAME}.msi", script)


def msix():
    from PIL import Image
    stage = WORK / "msix"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(BUNDLE, stage)
    assets = stage / "Assets"
    assets.mkdir()
    image = Image.open(ROOT / "assets/liubai.png")
    for filename, size in [("StoreLogo.png", 50), ("Square44x44Logo.png", 44), ("Square150x150Logo.png", 150)]:
        image.resize((size, size), Image.Resampling.LANCZOS).save(assets / filename)
    minimum = "10.0.22000.0" if ARCH == "arm64" else "10.0.19041.0"
    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
 xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
 xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
 IgnorableNamespaces="uap rescap">
 <Identity Name="Liubai.Desktop" Publisher="CN=Liubai" Version="{__version__}.0" ProcessorArchitecture="{ARCH}"/>
 <Properties><DisplayName>留白</DisplayName><PublisherDisplayName>Liubai contributors</PublisherDisplayName><Logo>Assets\\StoreLogo.png</Logo></Properties>
 <Dependencies><TargetDeviceFamily Name="Windows.Desktop" MinVersion="{minimum}" MaxVersionTested="10.0.26100.0"/></Dependencies>
 <Resources><Resource Language="zh-cn"/><Resource Language="en-us"/></Resources>
 <Applications><Application Id="Liubai" Executable="liubai.exe" EntryPoint="Windows.FullTrustApplication">
 <uap:VisualElements DisplayName="留白" Description="桌面待办与便签" BackgroundColor="transparent"
 Square44x44Logo="Assets\\Square44x44Logo.png" Square150x150Logo="Assets\\Square150x150Logo.png"/>
 </Application></Applications>
 <Capabilities><rescap:Capability Name="runFullTrust"/></Capabilities>
</Package>'''
    (stage / "AppxManifest.xml").write_text(manifest, encoding="utf-8")
    tool = shutil.which("makeappx.exe")
    if not tool:
        kit = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits/10/bin"
        candidates = sorted(kit.glob(f"*/{ARCH}/makeappx.exe")) or sorted(kit.glob("*/x64/makeappx.exe"))
        if not candidates:
            raise RuntimeError("Windows SDK MakeAppx.exe is required.")
        tool = candidates[-1]
    run(tool, "pack", "/d", stage, "/p", RELEASE / f"{NAME}-unsigned.msix", "/o")


def main():
    if os.name != "nt":
        raise SystemExit("Run Windows packaging on Windows.")
    WORK.mkdir(parents=True, exist_ok=True)
    RELEASE.mkdir(exist_ok=True)
    inno_setup()
    msi()
    msix()
    checksums(RELEASE)


if __name__ == "__main__":
    main()
