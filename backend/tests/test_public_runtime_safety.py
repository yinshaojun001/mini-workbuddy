from app.config import get_settings
from app.public_runtime.adapters.fortune import FortunePublicAdapter
from app.public_runtime.prompt import build_system_prompt


def test_public_run_events_do_not_duplicate_private_runtime_content(
    client, workspace, monkeypatch
):
    from tests.test_public_runtime_api import (
        birth_payload,
        configure_fakes,
    )

    configure_fakes(monkeypatch, workspace)
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
    from tests.test_public_runtime_api import FakeChartClient

    agent = next(item for item in client.get("/api/agents").json() if item["id"] == "fortune-bazi-agent")
    adapter = FortunePublicAdapter(get_settings(), FakeChartClient())
    prompt = build_system_prompt(
        workspace,
        agent,
        adapter.prompt_blocks(
            {"focus_topics": ["career"]},
            {"kind": "fortune", "pillars": {"day": "甲午"}},
        ),
    )
    assert "不得自行排盘" in prompt
    assert "不预测死亡" in prompt
    assert prompt.count("<TRUSTED_FORTUNE_DATA>") == 1
