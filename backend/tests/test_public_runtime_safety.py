import pytest

from app.config import get_settings
from app.public_runtime.adapters.fortune import FortunePublicAdapter
from app.public_runtime.adapters.dream import DreamPublicAdapter
from app.public_runtime.prompt import build_system_prompt
from tests.test_dream_public_adapter import dream_payload, reference_path


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


@pytest.mark.asyncio
async def test_dream_prompt_preserves_data_boundaries_and_safety_rules(client, workspace):
    agent = next(
        item for item in client.get("/api/agents").json() if item["id"] == "dream-analysis-agent"
    )
    adapter = DreamPublicAdapter.from_path(reference_path())
    prepared = await adapter.prepare(dream_payload())

    prompt = build_system_prompt(
        workspace,
        agent,
        adapter.prompt_blocks(prepared.input_data, prepared.context),
    )

    assert prompt.count("<USER_DREAM_DATA>") == 1
    assert prompt.count("<DREAM_REFERENCE_DATA>") == 1
    assert "梦中出现死亡、坠落、自伤、伤人" in prompt
    assert "现实中当前或即将自伤、伤人" in prompt
    assert "公开运行没有工具" in prompt
