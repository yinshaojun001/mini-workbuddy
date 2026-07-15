from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from app.errors import AppError
from app.storage.json_store import AtomicJsonStore


class SessionRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list(self) -> list[dict[str, Any]]:
        sessions = []
        for path in self.root.iterdir():
            metadata = path / "session.json"
            if metadata.is_file():
                sessions.append(json.loads(metadata.read_text(encoding="utf-8")))
        return sorted(sessions, key=lambda item: item["updated_at"], reverse=True)

    def get(self, session_id: str) -> dict[str, Any]:
        path = self.root / session_id / "session.json"
        if not path.is_file():
            raise AppError("SESSION_NOT_FOUND", "会话不存在", 404)
        return json.loads(path.read_text(encoding="utf-8"))

    def create(self, metadata: dict[str, Any]) -> dict[str, Any]:
        directory = self.root / metadata["id"]
        directory.mkdir(parents=True)
        AtomicJsonStore(directory / "session.json", metadata).write(metadata)
        (directory / "messages.jsonl").touch()
        return metadata

    def update(self, session_id: str, values: dict[str, Any]) -> dict[str, Any]:
        current = {**self.get(session_id), **values, "id": session_id}
        AtomicJsonStore(self.root / session_id / "session.json", current).write(current)
        return current

    def delete(self, session_id: str) -> None:
        self.get(session_id)
        shutil.rmtree(self.root / session_id)

    def messages(self, session_id: str) -> list[dict[str, Any]]:
        self.get(session_id)
        results = []
        path = self.root / session_id / "messages.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return results

    def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        self.get(session_id)
        with (self.root / session_id / "messages.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
