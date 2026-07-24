import json

from app.bootstrap.fortune import AGENT_ID, APP_ID, SKILL_ID, bootstrap_fortune


def test_fortune_resources_are_installed_without_tools(client, workspace):
    agents = json.loads((workspace / "agents.json").read_text())
    agent = next(item for item in agents if item["id"] == AGENT_ID)
    assert agent["tool_ids"] == []
    assert agent["skill_ids"] == [SKILL_ID]
    assert (workspace / "skills" / SKILL_ID / "SKILL.md").is_file()
    apps = json.loads((workspace / "apps.json").read_text())
    assert next(item for item in apps if item["id"] == APP_ID)["agent_id"] == AGENT_ID


def test_fortune_bootstrap_preserves_existing_resources(client, workspace):
    prompt = workspace / "agents" / AGENT_ID / "agent.md"
    skill = workspace / "skills" / SKILL_ID / "SKILL.md"
    prompt.write_text("管理员自定义 prompt", encoding="utf-8")
    skill.write_text("管理员自定义 skill", encoding="utf-8")
    bootstrap_fortune(workspace)
    assert prompt.read_text(encoding="utf-8") == "管理员自定义 prompt"
    assert skill.read_text(encoding="utf-8") == "管理员自定义 skill"
