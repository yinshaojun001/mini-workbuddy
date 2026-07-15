import json
from pathlib import Path
from typing import Any

from app.errors import AppError


class RunRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def append(self, run_id: str, event: dict[str, Any]) -> dict[str, Any]:
        path = self.root / f"{run_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def events(self, run_id: str) -> list[dict[str, Any]]:
        path = self.root / f"{run_id}.jsonl"
        if not path.is_file():
            raise AppError("RUN_NOT_FOUND", "运行记录不存在", 404)
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def list(self) -> list[dict[str, Any]]:
        records = []
        for path in self.root.glob("*.jsonl"):
            events = self.events(path.stem)
            if events:
                records.append(
                    {
                        "id": path.stem,
                        "session_id": events[0].get("data", {}).get("session_id"),
                        "agent_id": events[0].get("data", {}).get("agent_id"),
                        "status": events[-1]["type"].removeprefix("run."),
                        "started_at": events[0]["timestamp"],
                        "updated_at": events[-1]["timestamp"],
                        "event_count": len(events),
                    }
                )
        return sorted(records, key=lambda item: item["updated_at"], reverse=True)

