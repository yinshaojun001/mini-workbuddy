from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.public_runtime.events import PublicRunEventRepository


def event(sequence: int, event_type: str = "model.completed", **extra: object) -> dict:
    return {
        "sequence": sequence,
        "timestamp": f"2026-07-26T12:00:{sequence:02d}+00:00",
        "type": event_type,
        "mode": "report",
        "duration_ms": sequence * 10,
        "model_id": "deepseek-v4-flash",
        "error_code": None,
        **extra,
    }


def create_session(root, session_id="session-one"):
    (root / session_id).mkdir(parents=True)


def test_append_writes_only_safe_fields_to_the_session_run_directory(tmp_path):
    root = tmp_path / "public_sessions"
    create_session(root)
    repo = PublicRunEventRepository(root)

    stored = repo.append(
        "session-one",
        "run-one",
        event(
            1,
            "run.started",
            message="private question",
            prompt="private prompt",
            birth={"name": "Private Person"},
        ),
    )

    path = root / "session-one" / "runs" / "run-one.jsonl"
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8")) == stored == {
        "run_id": "run-one",
        "sequence": 1,
        "timestamp": "2026-07-26T12:00:01+00:00",
        "type": "run.started",
        "mode": "report",
        "duration_ms": 10,
        "model_id": "deepseek-v4-flash",
        "error_code": None,
    }
    assert "private" not in path.read_text(encoding="utf-8").lower()


def test_concurrent_append_keeps_every_event_and_recovers_sequence_order(tmp_path):
    root = tmp_path / "public_sessions"
    create_session(root)
    repo = PublicRunEventRepository(root)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda sequence: repo.append("session-one", "run-one", event(sequence)),
                reversed(range(1, 101)),
            )
        )

    result = repo.events("session-one")
    assert len(result["events"]) == 100
    assert [item["sequence"] for item in result["runs"][0]["events"]] == list(range(1, 101))


def test_events_ignores_damaged_lines_sorts_stably_and_derives_run_status(tmp_path):
    root = tmp_path / "public_sessions"
    create_session(root)
    repo = PublicRunEventRepository(root)
    repo.append("session-one", "run-completed", event(2, "run.completed"))
    repo.append("session-one", "run-completed", event(1, "run.started"))
    repo.append("session-one", "run-failed", event(1, "run.started"))
    repo.append("session-one", "run-failed", event(2, "run.failed", error_code="ENGINE_FAILED"))
    repo.append("session-one", "run-interrupted", event(1, "run.started"))
    with (root / "session-one" / "runs" / "run-completed.jsonl").open(
        "a", encoding="utf-8"
    ) as handle:
        handle.write("{definitely-not-json}\n")

    result = repo.events("session-one")

    assert [item["run_id"] for item in result["runs"]] == [
        "run-completed",
        "run-failed",
        "run-interrupted",
    ]
    assert {item["run_id"]: item["status"] for item in result["runs"]} == {
        "run-completed": "completed",
        "run-failed": "failed",
        "run-interrupted": "interrupted",
    }
    assert result["historical_events_unavailable"] is False
    assert len(result["events"]) == 5


def test_messages_without_run_files_are_reported_as_historical(tmp_path):
    session_dir = tmp_path / "public_sessions" / "historical"
    (session_dir / "runs").mkdir(parents=True)
    (session_dir / "messages.json").write_text(
        json.dumps([{"role": "assistant", "content": "old response"}]), encoding="utf-8"
    )

    result = PublicRunEventRepository(tmp_path / "public_sessions").events("historical")

    assert result == {
        "events": [],
        "runs": [],
        "historical_events_unavailable": True,
    }


def test_empty_new_session_does_not_claim_historical_events_are_missing(tmp_path):
    session_dir = tmp_path / "public_sessions" / "new"
    (session_dir / "runs").mkdir(parents=True)
    (session_dir / "messages.json").write_text("[]\n", encoding="utf-8")

    result = PublicRunEventRepository(tmp_path / "public_sessions").events("new")

    assert result["historical_events_unavailable"] is False


def test_append_does_not_recreate_a_missing_session_directory(tmp_path):
    root = tmp_path / "public_sessions"

    with pytest.raises(FileNotFoundError):
        PublicRunEventRepository(root).append("deleted", "run-one", event(1))

    assert not (root / "deleted").exists()


@pytest.mark.parametrize("terminal_type", ["model.failed", "agent.failed", "run.failed"])
def test_all_failure_terminal_events_derive_failed_status(tmp_path, terminal_type):
    root = tmp_path / "public_sessions"
    (root / "session-one" / "runs").mkdir(parents=True)
    repo = PublicRunEventRepository(root)
    repo.append("session-one", "run-one", event(1, "run.started"))
    repo.append("session-one", "run-one", event(2, terminal_type))

    assert repo.events("session-one")["runs"][0]["status"] == "failed"
