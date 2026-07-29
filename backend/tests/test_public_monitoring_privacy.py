from __future__ import annotations

import json

from app.storage.json_store import AtomicJsonStore

ORIGIN = {"origin": "http://localhost:5174"}
SENTINEL_NAME = "隐私哨兵张三"
SENTINEL_DATE = "1998-12-13"
SENTINEL_TIME = "12:34"
SENTINEL_QUESTION = "QUESTION_SENTINEL_7X9：请结合我的生日说明事业重点"
SENTINEL_REPORT = f"REPORT_SENTINEL_4Q2：{SENTINEL_NAME} 生于 {SENTINEL_DATE} {SENTINEL_TIME}"
SENTINEL_ANSWER = f"ANSWER_SENTINEL_8M3：{SENTINEL_NAME} 的出生时间是 {SENTINEL_TIME}"
SENTINEL_API_KEY = "API_KEY_SENTINEL_NEVER_PERSIST"
SENTINEL_CHART_PRIVATE = "CHART_PRIVATE_SENTINEL_NEVER_RETURN"
DREAM_TEXT_SENTINEL = "DREAM_TEXT_SENTINEL_2F8"
DREAM_CONTEXT_SENTINEL = "DREAM_CONTEXT_SENTINEL_6K1"
DREAM_REPORT_SENTINEL = "DREAM_REPORT_SENTINEL_9P4"


class PrivacyChartClient:
    async def calculate(self, birth, longitude):
        assert longitude > 100
        return {
            "chart": {
                "pillars": {
                    "year": {"ganZhi": "戊寅", "private": SENTINEL_CHART_PRIVATE},
                    "month": {"ganZhi": "甲子"},
                    "day": {"ganZhi": "乙丑"},
                    "hour": {"ganZhi": "丙午"},
                },
                "day_master": {"char": "乙", "private": SENTINEL_CHART_PRIVATE},
                "da_yun": {},
                "interactions": [],
                "solar_time": {"exact": SENTINEL_TIME},
                "calendar": {"exact": SENTINEL_DATE},
                "metadata": {"name": SENTINEL_NAME},
                "unexpected": SENTINEL_CHART_PRIVATE,
            },
            "policy": {"private": SENTINEL_CHART_PRIVATE},
            "attribution": {"private": SENTINEL_CHART_PRIVATE},
        }


class PrivacyAdapter:
    calls = 0

    async def complete(self, model, messages, tools):
        assert model["api_key"] == SENTINEL_API_KEY
        assert tools == []
        self.__class__.calls += 1
        content = SENTINEL_REPORT if self.calls == 1 else SENTINEL_ANSWER
        return {"content": content, "tool_calls": []}


class DreamPrivacyAdapter:
    async def complete(self, model, messages, tools):
        assert model["api_key"] == SENTINEL_API_KEY
        assert tools == []
        return {"content": DREAM_REPORT_SENTINEL, "tool_calls": []}


def _enable_model(workspace) -> None:
    store = AtomicJsonStore(workspace / "models.json", [])
    models = store.read()
    models[0]["api_key"] = SENTINEL_API_KEY
    store.write(models)


def _birth_payload() -> dict:
    return {
        "name": SENTINEL_NAME,
        "gender": "female",
        "birth_date": SENTINEL_DATE,
        "birth_time": SENTINEL_TIME,
        "birth_time_unknown": False,
        "province_code": "110000",
        "city_code": "110100",
        "true_solar_time": False,
        "focus_topics": ["career"],
    }


def _assert_absent(serialized: str, values: tuple[str, ...]) -> None:
    for value in values:
        assert value not in serialized, f"unexpected private value persisted or returned: {value}"


def test_public_monitoring_keeps_sensitive_data_out_of_default_and_permanent_storage(
    client,
    workspace,
    monkeypatch,
):
    from app.public_runtime import router
    from app.config import get_settings
    from app.public_runtime.adapters.fortune import FortunePublicAdapter
    from app.public_runtime.adapters.registry import (
        PublicAdapterRegistry,
        configure_public_adapter_registry,
    )

    _enable_model(workspace)
    PrivacyAdapter.calls = 0
    configure_public_adapter_registry(
        PublicAdapterRegistry(
            [FortunePublicAdapter(get_settings(), PrivacyChartClient())]
        )
    )
    monkeypatch.setattr(router, "adapter_factory", PrivacyAdapter)

    created = client.post(
        "/api/public/apps/fortune/sessions",
        json=_birth_payload(),
        headers=ORIGIN,
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["session"]["id"]

    report = client.post(
        f"/api/public/apps/fortune/sessions/{session_id}/report",
        headers=ORIGIN,
    )
    assert report.status_code == 200
    assert '"type": "run.completed"' in report.text
    question = client.post(
        f"/api/public/apps/fortune/sessions/{session_id}/messages",
        json={"content": SENTINEL_QUESTION},
        headers=ORIGIN,
    )
    assert question.status_code == 200
    assert '"type": "run.completed"' in question.text
    assert PrivacyAdapter.calls == 2

    session_dir = workspace / "public_sessions" / session_id
    internal_session = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
    visitor_cookie = client.cookies.get("fortune_visitor")
    assert visitor_cookie
    forbidden_internal_values = (
        internal_session["owner_hash"],
        internal_session["ip_hash"],
        internal_session["reservation_id"],
        visitor_cookie,
        SENTINEL_API_KEY,
        SENTINEL_CHART_PRIVATE,
    )

    default_response = client.get(f"/api/public-runs/{session_id}")
    assert default_response.status_code == 200, default_response.text
    default = default_response.json()
    default_serialized = json.dumps(default, ensure_ascii=False)
    _assert_absent(
        default_serialized,
        (
            SENTINEL_NAME,
            SENTINEL_DATE,
            SENTINEL_TIME,
            *forbidden_internal_values,
        ),
    )
    assert default["birth"] == {
        "name": "隐*****",
        "gender": "***",
        "birth_date": "****-**-**",
        "birth_time": "**:**",
        "birth_time_unknown": None,
        "province_code": "******",
        "city_code": "******",
        "true_solar_time": None,
        "focus_topics": ["***"],
    }
    assert default["chart"] == {
        "pillars": {
            "year": {"gan_zhi": "戊寅"},
            "month": {"gan_zhi": "甲子"},
            "day": {"gan_zhi": "乙丑"},
            "hour": {"gan_zhi": "丙午"},
        },
        "day_master": {"gan": "乙"},
    }
    default_messages = [message["content"] for message in default["messages"]]
    assert any("REPORT_SENTINEL_4Q2" in content for content in default_messages)
    assert any("QUESTION_SENTINEL_7X9" in content for content in default_messages)
    assert any("ANSWER_SENTINEL_8M3" in content for content in default_messages)

    sensitive_response = client.get(
        f"/api/public-runs/{session_id}",
        params={"include_sensitive": "true"},
    )
    assert sensitive_response.status_code == 200
    sensitive = sensitive_response.json()
    assert sensitive["birth"] == _birth_payload()
    assert [set(message) for message in sensitive["messages"]] == [
        {"id", "role", "content", "created_at"},
        {"id", "role", "content", "created_at"},
        {"id", "role", "content", "created_at"},
    ]
    sensitive_messages = [message["content"] for message in sensitive["messages"]]
    assert SENTINEL_REPORT in sensitive_messages
    assert SENTINEL_QUESTION in sensitive_messages
    assert SENTINEL_ANSWER in sensitive_messages
    sensitive_without_allowed_birth_and_messages = {
        **sensitive,
        "birth": {},
        "input": {"kind": "fortune", "fields": {}},
        "messages": [],
    }
    _assert_absent(
        json.dumps(sensitive_without_allowed_birth_and_messages, ensure_ascii=False),
        (
            SENTINEL_NAME,
            SENTINEL_DATE,
            SENTINEL_TIME,
            *forbidden_internal_values,
        ),
    )
    sensitive_keys = json.dumps(sensitive, ensure_ascii=False).lower()
    assert all(
        key not in sensitive_keys
        for key in ("owner_hash", "ip_hash", "reservation_id", "api_key", "prompt", "cookie")
    )

    event_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((session_dir / "runs").glob("*.jsonl"))
    )
    assert event_text
    _assert_absent(
        event_text,
        (
            SENTINEL_NAME,
            SENTINEL_DATE,
            SENTINEL_TIME,
            SENTINEL_QUESTION,
            SENTINEL_REPORT,
            SENTINEL_ANSWER,
            *forbidden_internal_values,
        ),
    )
    assert "prompt" not in event_text.lower()
    assert "cookie" not in event_text.lower()
    assert all(
        key not in event_text.lower()
        for key in ("owner_hash", "ip_hash", "reservation_id", "api_key")
    )

    metrics_path = workspace / "public_metrics.json"
    metrics_before_delete = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics_text = json.dumps(metrics_before_delete, ensure_ascii=False)
    _assert_absent(
        metrics_text,
        (
            session_id,
            SENTINEL_NAME,
            SENTINEL_DATE,
            SENTINEL_TIME,
            SENTINEL_QUESTION,
            SENTINEL_REPORT,
            SENTINEL_ANSWER,
            *forbidden_internal_values,
        ),
    )
    assert set(metrics_before_delete) == {"version", "apps"}
    assert all(
        key not in metrics_text.lower()
        for key in ("owner_hash", "ip_hash", "reservation_id", "api_key", "prompt", "cookie")
    )
    assert metrics_before_delete["apps"]["fortune"]["sessions_created"] == 1
    assert metrics_before_delete["apps"]["fortune"]["runs_completed"] == 2

    deleted = client.delete(f"/api/public-runs/{session_id}")
    assert deleted.status_code == 204, deleted.text
    assert not session_dir.exists()
    metrics_after_delete = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics_after_delete["apps"]["fortune"]["admin_deletions"] == 1
    assert metrics_after_delete["apps"]["fortune"]["sessions_created"] == 1
    assert metrics_after_delete["apps"]["fortune"]["runs_completed"] == 2
    _assert_absent(
        json.dumps(metrics_after_delete, ensure_ascii=False),
        (session_id, SENTINEL_NAME, SENTINEL_QUESTION, SENTINEL_REPORT, SENTINEL_ANSWER),
    )


def test_dream_monitoring_and_management_never_expose_private_markers(
    client,
    workspace,
    monkeypatch,
):
    from app.public_runtime import router
    from app.public_runtime.adapters.dream import DreamPublicAdapter
    from app.public_runtime.adapters.registry import (
        PublicAdapterRegistry,
        configure_public_adapter_registry,
    )
    from tests.test_dream_public_adapter import reference_path
    from tests.test_dream_public_api import enable_dream_app

    _enable_model(workspace)
    enable_dream_app(workspace)
    configure_public_adapter_registry(
        PublicAdapterRegistry([DreamPublicAdapter.from_path(reference_path())])
    )
    monkeypatch.setattr(router, "adapter_factory", DreamPrivacyAdapter)
    private_values = (
        DREAM_TEXT_SENTINEL,
        DREAM_CONTEXT_SENTINEL,
        DREAM_REPORT_SENTINEL,
    )
    created = client.post(
        "/api/public/apps/dream/sessions",
        json={
            "dream_text": f"我梦见旧屋积水，醒来后仍记得这个标记 {DREAM_TEXT_SENTINEL}。",
            "emotions": ["焦虑"],
            "recurring": False,
            "recent_context": f"最近的现实背景标记是 {DREAM_CONTEXT_SENTINEL}。",
        },
        headers=ORIGIN,
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["session"]["id"]

    report = client.post(
        f"/api/public/apps/dream/sessions/{session_id}/report",
        headers=ORIGIN,
    )
    assert report.status_code == 200, report.text
    assert DREAM_REPORT_SENTINEL in report.text

    session_dir = workspace / "public_sessions" / session_id
    allowed_session_text = (session_dir / "input.json").read_text(encoding="utf-8")
    allowed_messages_text = (session_dir / "messages.json").read_text(encoding="utf-8")
    assert DREAM_TEXT_SENTINEL in allowed_session_text
    assert DREAM_CONTEXT_SENTINEL in allowed_session_text
    assert DREAM_REPORT_SENTINEL in allowed_messages_text

    event_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((session_dir / "runs").glob("*.jsonl"))
    )
    _assert_absent(event_text, private_values)

    metrics_text = (workspace / "public_metrics.json").read_text(encoding="utf-8")
    _assert_absent(metrics_text, (session_id, *private_values))
    assert json.loads(metrics_text)["apps"]["dream"]["runs_completed"] == 1

    sse_events = [
        json.loads(line.removeprefix("data: "))
        for line in report.text.splitlines()
        if line.startswith("data: ")
    ]
    sse_metadata = [
        {**event, "data": {key: value for key, value in event["data"].items() if key != "content"}}
        for event in sse_events
    ]
    _assert_absent(json.dumps(sse_metadata, ensure_ascii=False), private_values)

    for include_sensitive in (False, True):
        detail = client.get(
            f"/api/public-runs/{session_id}",
            params={"include_sensitive": str(include_sensitive).lower()},
        )
        assert detail.status_code == 200, detail.text
        serialized = json.dumps(detail.json(), ensure_ascii=False)
        _assert_absent(serialized, private_values)
        assert detail.json()["messages"] == []
