from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from app.public_runtime.events import PublicRunEventRepository
from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository
from app.errors import AppError

SESSION_IDS = {
    "active": "00000000-0000-4000-8000-000000000001",
    "running": "00000000-0000-4000-8000-000000000002",
    "completed": "00000000-0000-4000-8000-000000000003",
    "failed": "00000000-0000-4000-8000-000000000004",
    "expired": "00000000-0000-4000-8000-000000000005",
    "detail": "00000000-0000-4000-8000-000000000006",
    "historical": "00000000-0000-4000-8000-000000000007",
    "reserved": "00000000-0000-4000-8000-000000000008",
    "committed": "00000000-0000-4000-8000-000000000009",
    "delete_running": "00000000-0000-4000-8000-000000000010",
    "dream_detail": "00000000-0000-4000-8000-000000000012",
}


def create_session(
    workspace,
    session_id: str,
    *,
    status: str = "chart_ready",
    updated_at: datetime | None = None,
    expires_at: datetime | None = None,
    question_count: int = 0,
    reservation_id: str | None = None,
    quota_committed: bool = False,
    owner_hash: str = "private-owner",
    ip_hash: str = "private-ip",
):
    now = updated_at or datetime.now(UTC)
    session = {
        "id": session_id,
        "app_id": "fortune",
        "owner_hash": owner_hash,
        "ip_hash": ip_hash,
        "status": status,
        "reservation_id": reservation_id,
        "quota_committed": quota_committed,
        "question_count": question_count,
        "created_at": (now - timedelta(minutes=1)).isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (expires_at or now + timedelta(hours=1)).isoformat(),
    }
    repo = PublicSessionRepository(workspace / "public_sessions")
    repo.create(
        session,
        {
            "name": "张三",
            "gender": "female",
            "birth_date": "1998-12-13",
            "birth_time": "12:00",
            "birth_time_unknown": False,
            "province_code": "110000",
            "city_code": "110100",
            "true_solar_time": False,
            "focus_topics": ["career"],
        },
        {
            "input": {"name": "CHART_INPUT_MUST_NOT_LEAK", "birth_date": "1998-12-13"},
            "calculation_policy": {"internal": "private-policy"},
            "pillars": {
                "year": {"ganZhi": "戊寅", "private": "hidden"},
                "month": {"ganZhi": "甲子"},
                "day": {"ganZhi": "乙丑"},
                "hour": {"ganZhi": "丙午"},
            },
            "day_master": {"gan": "乙", "private": "hidden"},
            "attribution": {"name": "private-engine"},
        },
    )
    return repo


def add_completed_run(workspace, session_id: str, run_id: str = "run-one") -> None:
    events = PublicRunEventRepository(workspace / "public_sessions")
    for sequence, event_type in enumerate(("run.started", "run.completed"), start=1):
        events.append(
            session_id,
            run_id,
            {
                "sequence": sequence,
                "timestamp": f"2026-07-26T12:00:0{sequence}+00:00",
                "type": event_type,
                "mode": "report",
                "duration_ms": sequence * 10,
                "model_id": "deepseek-v4-flash",
                "error_code": None,
            },
        )


def test_public_runs_list_filters_status_search_and_uses_stable_cursor(client, workspace):
    base = datetime.now(UTC)
    create_session(workspace, SESSION_IDS["active"], updated_at=base)
    create_session(workspace, SESSION_IDS["running"], status="question_running", updated_at=base - timedelta(minutes=1))
    create_session(workspace, SESSION_IDS["completed"], status="report_ready", question_count=20, updated_at=base - timedelta(minutes=2))
    create_session(workspace, SESSION_IDS["failed"], status="report_failed", updated_at=base - timedelta(minutes=3))
    create_session(
        workspace,
        SESSION_IDS["expired"],
        updated_at=base - timedelta(minutes=4),
        expires_at=base - timedelta(seconds=1),
    )
    add_completed_run(workspace, SESSION_IDS["active"])

    first = client.get("/api/public-runs", params={"limit": 2}).json()
    assert [item["session_id"] for item in first["items"]] == [SESSION_IDS["active"], SESSION_IDS["running"]]
    assert first["next_cursor"]
    second = client.get(
        "/api/public-runs", params={"limit": 2, "cursor": first["next_cursor"]}
    ).json()
    assert [item["session_id"] for item in second["items"]] == [
        SESSION_IDS["completed"],
        SESSION_IDS["failed"],
    ]
    assert not ({item["session_id"] for item in first["items"]} & {item["session_id"] for item in second["items"]})
    reused = client.get(
        "/api/public-runs",
        params={"limit": 2, "cursor": first["next_cursor"], "status": "active"},
    )
    assert reused.status_code == 422

    assert client.get("/api/public-runs", params={"status": "expired"}).json()["items"][0][
        "session_id"
    ] == SESSION_IDS["expired"]
    assert client.get("/api/public-runs", params={"query": "0004"}).json()["items"][0][
        "status"
    ] == "failed"
    active = client.get("/api/public-runs", params={"status": "active"}).json()["items"][0]
    assert active["run_count"] == 1
    assert active["last_run_status"] == "completed"
    serialized = json.dumps(first, ensure_ascii=False).lower()
    assert all(value not in serialized for value in ("private-owner", "private-ip", "reservation"))


def test_public_runs_rejects_invalid_cursor(client):
    response = client.get("/api/public-runs", params={"cursor": "not-a-valid-cursor"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_cursor_survives_equal_timestamps_and_a_deleted_anchor(client, workspace):
    updated_at = datetime.now(UTC)
    session_ids = [f"00000000-0000-4000-8000-{value:012d}" for value in (101, 102, 103)]
    for session_id in session_ids:
        create_session(workspace, session_id, updated_at=updated_at)

    first = client.get("/api/public-runs", params={"limit": 1}).json()
    assert first["items"][0]["session_id"] == session_ids[-1]
    PublicSessionRepository(workspace / "public_sessions").delete(session_ids[-1])

    second = client.get(
        "/api/public-runs", params={"limit": 1, "cursor": first["next_cursor"]}
    ).json()
    assert second["items"][0]["session_id"] == session_ids[-2]


def test_list_skips_a_session_deleted_between_scan_and_summary(
    client, workspace, monkeypatch
):
    deleted_id = "00000000-0000-4000-8000-000000000201"
    surviving_id = "00000000-0000-4000-8000-000000000202"
    create_session(workspace, deleted_id)
    create_session(workspace, surviving_id)
    original_messages = PublicSessionRepository.messages

    def concurrent_messages(self, session_id):
        if session_id == deleted_id:
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404)
        return original_messages(self, session_id)

    monkeypatch.setattr(PublicSessionRepository, "messages", concurrent_messages)

    response = client.get("/api/public-runs")

    assert response.status_code == 200
    assert [item["session_id"] for item in response.json()["items"]] == [surviving_id]


def test_public_run_paths_reject_non_uuid_and_encoded_separators(client, workspace):
    outside = workspace / "outside-marker"
    outside.write_text("must remain", encoding="utf-8")

    for unsafe in ("not-a-uuid", "..%252Foutside-marker", "%252e%252e%252foutside-marker"):
        assert client.get(f"/api/public-runs/{unsafe}").status_code == 404
        assert client.delete(f"/api/public-runs/{unsafe}").status_code == 404

    assert outside.read_text(encoding="utf-8") == "must remain"


def test_public_run_detail_masks_birth_and_never_returns_chart_input(client, workspace):
    session_id = SESSION_IDS["detail"]
    repo = create_session(workspace, session_id)
    repo.append_messages(
        session_id,
        [{"id": "message-one", "role": "assistant", "content": "张三 female 1998-12-13 12:00 110000 110100 career", "created_at": "now"}],
    )
    add_completed_run(workspace, session_id)
    malicious_path = workspace / "public_sessions" / session_id / "runs" / "malicious.jsonl"
    malicious_path.write_text(
        json.dumps(
            {
                "run_id": "malicious",
                "sequence": 1,
                "timestamp": "2026-07-26T12:00:03+00:00",
                "type": "run.completed",
                "mode": {"message": "EVENT_VALUE_MUST_NOT_LEAK"},
                "duration_ms": 1,
                "model_id": {"api_key": "EVENT_VALUE_MUST_NOT_LEAK"},
                "error_code": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    masked_response = client.get(f"/api/public-runs/{session_id}")
    assert masked_response.status_code == 200
    masked = masked_response.json()
    masked_text = json.dumps(masked, ensure_ascii=False)
    assert masked["input"] == {"kind": "fortune", "fields": masked["birth"]}
    assert masked["context"] == {"kind": "fortune", "summary": masked["chart"]}
    assert masked["birth"]["name"] != "张三"
    assert masked["birth"]["birth_date"] == "****-**-**"
    assert masked["birth"]["birth_time"] == "**:**"
    assert masked["chart"] == {
        "pillars": {
            "year": {"gan_zhi": "戊寅"},
            "month": {"gan_zhi": "甲子"},
            "day": {"gan_zhi": "乙丑"},
            "hour": {"gan_zhi": "丙午"},
        },
        "day_master": {"gan": "乙"},
    }
    assert masked["runs"][0]["status"] == "completed"
    assert masked["historical_events_unavailable"] is False
    assert "张三" not in masked["messages"][0]["content"]
    assert "1998-12-13" not in masked["messages"][0]["content"]
    assert "12:00" not in masked["messages"][0]["content"]
    assert "female" not in masked["messages"][0]["content"]
    assert "110000" not in masked["messages"][0]["content"]
    assert "110100" not in masked["messages"][0]["content"]
    assert "career" not in masked["messages"][0]["content"]
    assert all(
        term not in masked_text
        for term in (
            "private-owner",
            "private-ip",
            "CHART_INPUT_MUST_NOT_LEAK",
            "private-policy",
            "private-engine",
            "reservation_id",
            "EVENT_VALUE_MUST_NOT_LEAK",
        )
    )

    sensitive = client.get(
        f"/api/public-runs/{session_id}", params={"include_sensitive": "true"}
    ).json()
    assert sensitive["birth"] == {
        "name": "张三",
        "gender": "female",
        "birth_date": "1998-12-13",
        "birth_time": "12:00",
        "birth_time_unknown": False,
        "province_code": "110000",
        "city_code": "110100",
        "true_solar_time": False,
        "focus_topics": ["career"],
    }
    assert sensitive["messages"][0]["content"] == "张三 female 1998-12-13 12:00 110000 110100 career"
    assert "CHART_INPUT_MUST_NOT_LEAK" not in json.dumps(sensitive, ensure_ascii=False)


def test_dream_detail_never_exposes_text_context_or_messages(client, workspace):
    private_dream = "PRIVATE_DREAM_TEXT_7X9 我梦见旧屋积水并一直寻找出口。"
    private_context = "PRIVATE_RECENT_CONTEXT_4Q2 最近正在搬家。"
    now = datetime.now(UTC)
    session = {
        "id": SESSION_IDS["dream_detail"],
        "app_id": "dream",
        "owner_hash": "private-owner",
        "ip_hash": "private-ip",
        "status": "report_ready",
        "reservation_id": None,
        "quota_committed": True,
        "question_count": 1,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=1)).isoformat(),
    }
    repo = PublicSessionRepository(workspace / "public_sessions")
    repo.create(
        session,
        {
            "dream_text": private_dream,
            "emotions": ["焦虑"],
            "recurring": True,
            "recent_context": private_context,
        },
        {
            "kind": "dream",
            "summary": {"emotions": ["焦虑"], "recurring": True},
            "traditional_references": [
                {"symbol_id": "house", "label": "房屋", "quote": "PRIVATE_QUOTE"},
                {"symbol_id": "water", "label": "水", "quote": "PRIVATE_QUOTE"},
            ],
        },
    )
    repo.append_messages(
        session["id"],
        [
            {"id": "m1", "role": "user", "content": private_dream, "created_at": now.isoformat()},
            {"id": "m2", "role": "assistant", "content": "PRIVATE_REPORT", "created_at": now.isoformat()},
        ],
    )

    for include_sensitive in (False, True):
        response = client.get(
            f"/api/public-runs/{session['id']}",
            params={"include_sensitive": str(include_sensitive).lower()},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["input"] == {
            "kind": "dream",
            "fields": {
                "emotions": ["焦虑"],
                "recurring": True,
                "dream_length": len(private_dream),
                "has_recent_context": True,
            },
        }
        assert payload["context"] == {
            "kind": "dream",
            "summary": {
                "symbols": [
                    {"id": "house", "label": "房屋"},
                    {"id": "water", "label": "水"},
                ]
            },
        }
        assert payload["messages"] == []
        serialized = json.dumps(payload, ensure_ascii=False)
        for marker in (private_dream, private_context, "PRIVATE_QUOTE", "PRIVATE_REPORT"):
            assert marker not in serialized


def test_historical_session_detail_reports_events_unavailable(client, workspace):
    session_id = SESSION_IDS["historical"]
    repo = create_session(workspace, session_id)
    repo.append_messages(
        session_id,
        [{"id": "old", "role": "assistant", "content": "old report", "created_at": "then"}],
    )

    detail = client.get(f"/api/public-runs/{session_id}").json()

    assert detail["messages"][0]["content"] == "old report"
    assert detail["runs"] == []
    assert detail["historical_events_unavailable"] is True


def test_public_run_stats_returns_per_app_and_derived_total(client, workspace):
    metrics = PublicMetricsRepository(workspace / "public_metrics.json")
    metrics.session_created("fortune")
    metrics.run_started("fortune")
    metrics.run_completed("fortune", "report", 120)

    response = client.get("/api/public-runs/stats")

    assert response.status_code == 200
    assert response.json()["apps"]["fortune"]["sessions_created"] == 1
    assert response.json()["total"]["average_duration_ms"] == 120


def test_public_run_stats_whitelists_tampered_metric_values(client, workspace):
    (workspace / "public_metrics.json").write_text(
        json.dumps(
            {
                "version": 99,
                "apps": {
                    "fortune": {
                        "sessions_created": 3,
                        "runs_started": "private-session-id",
                        "runs_completed": 1,
                        "total_duration_ms": 50,
                        "reports_failed": -2,
                        "errors": {
                            "MODEL_TIMEOUT": 1,
                            "RAW_PRIVATE_EXCEPTION": 99,
                        },
                        "owner_hash": "must-not-leak",
                    }
                },
                "session_id": "must-not-leak",
            }
        ),
        encoding="utf-8",
    )

    payload = client.get("/api/public-runs/stats").json()

    assert payload["version"] == 1
    assert payload["apps"]["fortune"]["sessions_created"] == 3
    assert payload["apps"]["fortune"]["runs_started"] == 0
    assert payload["apps"]["fortune"]["reports_failed"] == 0
    assert payload["apps"]["fortune"]["errors"] == {"MODEL_TIMEOUT": 1}
    assert "must-not-leak" not in json.dumps(payload)


def test_admin_delete_rejects_running_and_releases_only_uncommitted_quota(client, workspace):
    quota = QuotaRepository(workspace / "public_usage")
    reservation = quota.reserve("fortune", "owner-a", "ip-a", 3)
    create_session(
        workspace,
        SESSION_IDS["reserved"],
        reservation_id=reservation,
        owner_hash="owner-a",
        ip_hash="ip-a",
    )
    committed = quota.reserve("fortune", "owner-b", "ip-b", 3)
    quota.commit("fortune", "owner-b", "ip-b", committed)
    create_session(
        workspace,
        SESSION_IDS["committed"],
        reservation_id=committed,
        quota_committed=True,
        owner_hash="owner-b",
        ip_hash="ip-b",
    )
    create_session(workspace, SESSION_IDS["delete_running"], status="report_running")

    conflict = client.delete(f"/api/public-runs/{SESSION_IDS['delete_running']}")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "SESSION_RUNNING"
    assert (workspace / "public_sessions" / SESSION_IDS["delete_running"]).exists()

    assert client.delete(f"/api/public-runs/{SESSION_IDS['reserved']}").status_code == 204
    assert quota.remaining("fortune", "owner-a", "ip-a", 3) == 3
    assert client.delete(f"/api/public-runs/{SESSION_IDS['committed']}").status_code == 204
    assert quota.remaining("fortune", "owner-b", "ip-b", 3) == 2

    metrics = PublicMetricsRepository(workspace / "public_metrics.json")
    assert metrics.read()["apps"]["fortune"]["admin_deletions"] == 2
    missing = client.delete(f"/api/public-runs/{SESSION_IDS['reserved']}")
    assert missing.status_code == 404
    assert metrics.read()["apps"]["fortune"]["admin_deletions"] == 2


def test_concurrent_admin_delete_has_one_winner_and_one_metric(client, workspace):
    from app.public_runtime.admin_router import service

    session_id = "00000000-0000-4000-8000-000000000011"
    create_session(workspace, session_id)

    def remove() -> int:
        try:
            service().delete(session_id)
            return 204
        except AppError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(lambda _: remove(), range(2)))

    assert results == [204, 404]
    metrics = PublicMetricsRepository(workspace / "public_metrics.json").read()
    assert metrics["apps"]["fortune"]["admin_deletions"] == 1
