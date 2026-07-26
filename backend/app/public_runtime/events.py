from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from threading import RLock
from typing import Any


class PublicRunEventRepository:
    _lock = RLock()
    _event_fields = (
        "run_id",
        "sequence",
        "timestamp",
        "type",
        "mode",
        "duration_ms",
        "model_id",
        "error_code",
    )

    def __init__(self, root: Path) -> None:
        self.root = root

    def append(
        self,
        session_id: str,
        run_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        stored = self._sanitize_event(event, run_id)
        with self._lock:
            runs_directory = self.root / session_id / "runs"
            runs_directory.mkdir(exist_ok=True)
            with (runs_directory / f"{run_id}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(stored, ensure_ascii=False) + "\n")
        return stored

    def events(self, session_id: str) -> dict[str, Any]:
        runs_directory = self.root / session_id / "runs"
        with self._lock:
            paths = sorted(runs_directory.glob("*.jsonl")) if runs_directory.is_dir() else []
            events = [
                event
                for path in paths
                for event in self._read_events(path)
            ]
            historical_events_unavailable = not paths and self._has_messages(session_id)

        events.sort(key=self._event_sort_key)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            grouped[event["run_id"]].append(event)

        runs = []
        for run_id in sorted(grouped):
            run_events = sorted(grouped[run_id], key=self._run_event_sort_key)
            runs.append(
                {
                    "run_id": run_id,
                    "status": self._status(run_events),
                    "events": run_events,
                }
            )

        return {
            "events": events,
            "runs": runs,
            "historical_events_unavailable": historical_events_unavailable,
        }

    @classmethod
    def _sanitize_event(cls, event: dict[str, Any], run_id: str) -> dict[str, Any]:
        return {
            field: run_id if field == "run_id" else event[field]
            for field in cls._event_fields
            if field == "run_id" or field in event
        }

    @classmethod
    def _read_events(cls, path: Path) -> list[dict[str, Any]]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

        events = []
        for line in lines:
            try:
                value = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(value, dict):
                events.append(cls._sanitize_event(value, path.stem))
        return events

    def _has_messages(self, session_id: str) -> bool:
        try:
            messages = json.loads(
                (self.root / session_id / "messages.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return False
        return isinstance(messages, list) and bool(messages)

    @staticmethod
    def _sequence(event: dict[str, Any]) -> tuple[int, str]:
        sequence = event.get("sequence")
        if isinstance(sequence, int):
            return sequence, ""
        return 0, str(sequence or "")

    @classmethod
    def _event_sort_key(cls, event: dict[str, Any]) -> tuple[str, str, int, str]:
        sequence, fallback = cls._sequence(event)
        return (
            str(event.get("timestamp") or ""),
            str(event.get("run_id") or ""),
            sequence,
            fallback,
        )

    @classmethod
    def _run_event_sort_key(cls, event: dict[str, Any]) -> tuple[int, str, str]:
        sequence, fallback = cls._sequence(event)
        return sequence, fallback, str(event.get("timestamp") or "")

    @staticmethod
    def _status(events: list[dict[str, Any]]) -> str:
        if not events:
            return "interrupted"
        terminal_type = events[-1].get("type")
        if terminal_type == "run.completed":
            return "completed"
        if terminal_type in {"model.failed", "agent.failed", "run.failed"}:
            return "failed"
        return "interrupted"
