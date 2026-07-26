from app.public_runtime.prompt import build_system_prompt


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
