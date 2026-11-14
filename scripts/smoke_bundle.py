#!/usr/bin/env python3
"""Launch the packaged application with isolated data and check persistence."""

import json
import os
import platform
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
binary = ROOT / "dist/liubai" / ("liubai.exe" if os.name == "nt" else "liubai")
with binary.open("rb") as stream:
    header = stream.read(64)
    if os.name == "nt":
        assert header[:2] == b"MZ"
        stream.seek(struct.unpack_from("<I", header, 0x3C)[0] + 4)
        machine = struct.unpack("<H", stream.read(2))[0]
        expected = 0xAA64 if platform.machine().lower() in ("arm64", "aarch64") else 0x8664
    else:
        assert header[:4] == b"\x7fELF"
        machine = struct.unpack_from("<H", header, 18)[0]
        expected = 183 if platform.machine().lower() in ("arm64", "aarch64") else 62
    assert machine == expected, f"Incorrect binary architecture: {machine} != {expected}"
with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    subprocess.run([str(binary), "--no-tray", "--smoke-test", "--data-dir", directory], env=env, check=True, timeout=30)
    data = json.loads((Path(directory) / "data.json").read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert len(data["settings"]["geometry"]) == 4
    assert data["tasks"] == [] and data["notes"] == []
print("Packaged app passed: native binary architecture, startup, UI initialization, shutdown, local persistence.")
