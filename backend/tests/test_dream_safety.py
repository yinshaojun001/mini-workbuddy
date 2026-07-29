import pytest

from tests.test_dream_public_api import configure_dream_fakes, create_dream_session
from tests.test_dream_public_adapter import dream_payload
from tests.test_public_runtime_api import ORIGIN


class SafetyRoutingAdapter:
    calls: list[dict] = []

    async def complete(self, model, messages, tools):
        assert tools == []
        system = messages[0]["content"]
        self.__class__.calls.append({"system": system, "tools": tools})
        if "这不是梦，我现在已经准备伤害自己" in system:
            content = (
                "先停止普通象征分析。请立即远离危险物品，联系身边可信任的人陪伴你，"
                "并联系所在地紧急服务或危机支持。"
            )
        else:
            content = "这是梦中的紧张内容，不自动代表现实危险，可以继续理解其中的害怕与压力。"
        return {"content": content, "tool_calls": []}


@pytest.mark.parametrize(
    ("text", "expects_crisis"),
    [
        ("我梦见自己从楼上掉下来，醒来后很害怕，现实中现在是安全的。", False),
        ("我梦见有人追杀我，但现实中没有伤害自己的想法，也没有伤害他人的打算。", False),
        ("这不是梦，我现在已经准备伤害自己，而且手边已有危险物品。", True),
    ],
)
def test_dream_violence_and_current_danger_follow_distinct_safety_paths(
    client, workspace, monkeypatch, text, expects_crisis
):
    from app.public_runtime import router

    configure_dream_fakes(monkeypatch, workspace)
    SafetyRoutingAdapter.calls.clear()
    monkeypatch.setattr(router, "adapter_factory", SafetyRoutingAdapter)
    created = create_dream_session(client, dream_payload(dream_text=text, recent_context=None))

    response = client.post(
        f"/api/public/apps/dream/sessions/{created['session']['id']}/report",
        headers=ORIGIN,
    )

    assert response.status_code == 200, response.text
    restored = client.get(
        f"/api/public/apps/dream/sessions/{created['session']['id']}"
    ).json()
    answer = restored["messages"][0]["content"]
    system = SafetyRoutingAdapter.calls[0]["system"]
    assert "梦中出现死亡、坠落、自伤、伤人" in system
    assert "现实中当前或即将自伤、伤人" in system
    assert SafetyRoutingAdapter.calls[0]["tools"] == []
    if expects_crisis:
        assert "停止普通象征分析" in answer
        assert "可信任的人" in answer
        assert "紧急服务或危机支持" in answer
    else:
        assert "不自动代表现实危险" in answer
        assert "紧急服务或危机支持" not in answer
