from __future__ import annotations

import json
import shutil
from pathlib import Path
from threading import RLock
from typing import Any

from app.errors import AppError
from app.storage.json_store import AtomicJsonStore


class PublicSessionRepository:
    _lock = RLock()

    def __init__(self, root: Path) -> None:
        self.root = root

    def create(self, session: dict, input_data: dict, context: dict) -> dict:
        with self._lock:
            directory = self.root / session["id"]
            directory.mkdir(parents=True)
            (directory / "runs").mkdir()
            AtomicJsonStore(directory / "session.json", session).write(session)
            AtomicJsonStore(directory / "input.json", input_data).write(input_data)
            AtomicJsonStore(directory / "context.json", context).write(context)
            AtomicJsonStore(directory / "messages.json", []).write([])
        return session

    def get(self, session_id: str) -> dict[str, Any]:
        path = self.root / session_id / "session.json"
        if not path.is_file():
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404) from exc

    def get_owned(self, session_id: str, owner_hash: str) -> dict[str, Any]:
        session = self.get(session_id)
        if not __import__("hmac").compare_digest(session["owner_hash"], owner_hash):
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404)
        return session

    def update(self, session_id: str, values: dict) -> dict:
        with self._lock:
            session = {**self.get(session_id), **values, "id": session_id}
            AtomicJsonStore(self.root / session_id / "session.json", session).write(session)
            return session

    def claim_run(self, session_id: str, owner_hash: str, mode: str, max_questions: int) -> dict:
        with self._lock:
            session = self.get_owned(session_id, owner_hash)
            allowed = (
                {"context_ready", "chart_ready", "report_failed", "interrupted"}
                if mode == "report"
                else {"report_ready"}
            )
            if session["status"] in {"report_running", "question_running"}:
                raise AppError("RUN_ALREADY_ACTIVE", "当前会话已有解读正在生成", 409)
            if session["status"] not in allowed:
                code = "REPORT_ALREADY_GENERATED" if mode == "report" else "REPORT_REQUIRED"
                raise AppError(code, "当前会话状态不允许此操作", 409)
            if mode == "question" and session["question_count"] >= max_questions:
                raise AppError("QUESTION_LIMIT_EXCEEDED", "本次会话的追问次数已经用完", 429)
            running = "report_running" if mode == "report" else "question_running"
            AtomicJsonStore(self.root / session_id / "session.json", session).write(
                {**session, "status": running}
            )
            return session

    def context(self, session_id: str) -> dict:
        self.get(session_id)
        directory = self.root / session_id
        try:
            context_path = directory / "context.json"
            if context_path.is_file():
                return json.loads(context_path.read_text(encoding="utf-8"))
            legacy = json.loads((directory / "chart.json").read_text(encoding="utf-8"))
            return legacy if legacy.get("kind") else {"kind": "fortune", **legacy}
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404) from exc

    def input_data(self, session_id: str) -> dict:
        self.get(session_id)
        try:
            return json.loads((self.root / session_id / "input.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404) from exc

    def chart(self, session_id: str) -> dict:
        return self.context(session_id)

    def birth_input(self, session_id: str) -> dict:
        return self.input_data(session_id)

    def messages(self, session_id: str) -> list[dict]:
        self.get(session_id)
        return AtomicJsonStore(self.root / session_id / "messages.json", []).read()

    def append_messages(self, session_id: str, messages: list[dict]) -> None:
        with self._lock:
            store = AtomicJsonStore(self.root / session_id / "messages.json", [])
            current = store.read()
            store.write([*current, *messages])

    def delete(self, session_id: str, owner_hash: str | None = None) -> dict:
        with self._lock:
            session = self.get(session_id) if owner_hash is None else self.get_owned(session_id, owner_hash)
            shutil.rmtree(self.root / session_id)
            return session

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self.get(session_id)
            try:
                return {
                    "session": session,
                    "input": self.input_data(session_id),
                    "context": self.context(session_id),
                    "messages": self.messages(session_id),
                }
            except (OSError, json.JSONDecodeError, AppError) as exc:
                raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404) from exc

    def delete_for_admin(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self.get(session_id)
            if session.get("status") in {"report_running", "question_running"}:
                raise AppError("SESSION_RUNNING", "当前运行结束后才能删除会话", 409)
            try:
                shutil.rmtree(self.root / session_id)
            except FileNotFoundError as exc:
                raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404) from exc
            return session

    def all(self) -> list[dict]:
        if not self.root.exists():
            return []
        sessions = []
        for directory in self.root.iterdir():
            if directory.is_dir():
                try:
                    sessions.append(self.get(directory.name))
                except AppError:
                    continue
        return sessions
