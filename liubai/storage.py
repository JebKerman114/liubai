"""Validated, atomic local storage. No Qt or network dependencies."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def data_directory() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Liubai"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "liubai"


def validate(data: object) -> dict:
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("不是有效的留白数据文件（需要 version: 1）。")
    for kind in ("tasks", "notes"):
        items = data.get(kind)
        if not isinstance(items, list):
            raise ValueError(f"数据文件缺少 {kind} 列表。")
        ids = set()
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                raise ValueError("数据记录缺少有效标识。")
            if item["id"] in ids:
                raise ValueError("数据文件包含重复标识。")
            ids.add(item["id"])
            keys = ("text",) if kind == "tasks" else ("title", "body")
            if any(not isinstance(item.get(key), str) for key in keys):
                raise ValueError("数据记录的文本格式不正确。")
            if kind == "tasks" and not isinstance(item.get("done"), bool):
                raise ValueError("待办完成状态格式不正确。")
            if kind == "notes" and (type(item.get("color", 0)) is not int or not 0 <= item.get("color", 0) <= 3):
                raise ValueError("便签颜色格式不正确。")
            for key in ("created", "updated"):
                if not isinstance(item.get(key), str):
                    raise ValueError("数据记录缺少时间。")
                try:
                    datetime.fromisoformat(item[key])
                except ValueError as exc:
                    raise ValueError("数据记录的时间格式不正确。") from exc
    if not isinstance(data.get("settings", {}), dict):
        raise ValueError("设置格式不正确。")
    return data


class Store:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or data_directory()
        self.path = self.directory / "data.json"
        self.backup = self.directory / "data.backup.json"
        self.warning = ""
        self.data = {"version": 1, "tasks": [], "notes": [], "settings": {}}
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.exists():
            try:
                self.data = self.read(self.path)
            except (OSError, ValueError) as exc:
                # Preserve the damaged file before attempting automatic recovery.
                damaged = self.directory / f"data.damaged-{uuid4().hex[:8]}.json"
                shutil.copy2(self.path, damaged)
                if self.backup.exists():
                    self.data = self.read(self.backup)
                    self.warning = f"已从备份恢复。原文件保存在 {damaged}"
                else:
                    raise ValueError(f"无法读取数据，原文件已保留在 {damaged}。\n{exc}") from exc

    @staticmethod
    def read(path: Path) -> dict:
        return validate(json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        validate(self.data)
        fd, temporary = tempfile.mkstemp(prefix=".data-", suffix=".json", dir=self.directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            if self.path.exists():
                try:
                    self.read(self.path)
                except (OSError, ValueError):
                    pass  # Never replace a good backup with a corrupt file.
                else:
                    shutil.copy2(self.path, self.backup)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add_task(self, text: str) -> dict | None:
        text = text.strip()
        if not text:
            return None
        task = {"id": uuid4().hex, "text": text, "done": False, "created": now(), "updated": now()}
        self.data["tasks"].append(task)
        return task

    def add_note(self) -> dict:
        note = {"id": uuid4().hex, "title": "", "body": "", "color": 0, "created": now(), "updated": now()}
        self.data["notes"].insert(0, note)
        return note
