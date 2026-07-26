from app.public_runtime.prompt import build_system_prompt


def test_public_run_events_do_not_duplicate_private_runtime_content(
    client, workspace, monkeypatch
):
    from app.public_runtime import router
    from tests.test_public_runtime_api import (
        FakeChartClient,
        RecordingAdapter,
        birth_payload,
        enable_model,
    )

    enable_model(workspace)
    RecordingAdapter.calls.clear()
    monkeypatch.setattr(router, "chart_client_factory", FakeChartClient)
    monkeypatch.setattr(router, "adapter_factory", RecordingAdapter)
    created = client.post(
        "/api/public/apps/fortune/sessions",
        json=birth_payload(),
        headers={"origin": "http://localhost:5174"},
    ).json()
    session_id = created["session"]["id"]

    response = client.post(
        f"/api/public/apps/fortune/sessions/{session_id}/report",
        headers={"origin": "http://localhost:5174"},
    )

    event_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (workspace / "public_sessions" / session_id / "runs").glob("*.jsonl")
    )
    assert "测试者" not in event_text
    assert "完整的初始解读报告" not in event_text
    assert "克制、具体的命理解读" not in event_text
    assert "test-key" not in event_text
    assert "message" not in event_text.lower()
    assert '"type": "agent.started"' not in response.text
    assert '"type": "model.started"' not in response.text
    assert '"model_id"' not in response.text


def test_prompt_keeps_untrusted_instructions_outside_trusted_chart(client, workspace):
    agent = next(item for item in client.get("/api/agents").json() if item["id"] == "fortune-bazi-agent")
    prompt = build_system_prompt(
        workspace,
        agent,
        {"chart": {"pillars": {"day": "甲午"}}},
        {"focus_topics": ["career"]},
    )
    assert "不得自行排盘" in prompt
    assert "不预测死亡" in prompt
    assert prompt.count("<TRUSTED_FORTUNE_DATA>") == 1
