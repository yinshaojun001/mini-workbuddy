from datetime import UTC, datetime
from pathlib import Path

from app.storage.json_store import AtomicJsonStore

SKILL_ID = "bazi-interpreter"
AGENT_ID = "fortune-bazi-agent"
APP_ID = "fortune"


def _asset(name: str) -> str:
    return (Path(__file__).parent / "assets" / name).read_text(encoding="utf-8")


def bootstrap_fortune(root: Path) -> None:
    timestamp = datetime.now(UTC).isoformat()

    skill_root = root / "skills" / SKILL_ID
    skill_root.mkdir(parents=True, exist_ok=True)
    if not (skill_root / "SKILL.md").exists():
        (skill_root / "SKILL.md").write_text(_asset("bazi-interpreter/SKILL.md"), encoding="utf-8")
    if not (skill_root / "metadata.json").exists():
        AtomicJsonStore(skill_root / "metadata.json", {}).write(
            {
                "id": SKILL_ID,
                "name": "八字命理解读",
                "description": "只解释可信排盘结果的克制型八字解读规范",
                "enabled": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

    agents_store = AtomicJsonStore(root / "agents.json", [])
    agents = agents_store.read()
    if not any(agent["id"] == AGENT_ID for agent in agents):
        work_directory = root / "runtime" / AGENT_ID
        work_directory.mkdir(parents=True, exist_ok=True)
        prompt_root = root / "agents" / AGENT_ID
        prompt_root.mkdir(parents=True, exist_ok=True)
        (prompt_root / "agent.md").write_text(_asset("fortune-agent.md"), encoding="utf-8")
        agents.append(
            {
                "id": AGENT_ID,
                "name": "知命八字 Agent",
                "description": "知命公开应用的固定八字解读 Agent",
                "model_id": "deepseek-default",
                "tool_ids": [],
                "skill_ids": [SKILL_ID],
                "work_directory": str(work_directory.resolve()),
                "enabled": True,
                "is_builtin": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        agents_store.write(agents)
    else:
        prompt_root = root / "agents" / AGENT_ID
        prompt_root.mkdir(parents=True, exist_ok=True)
        if not (prompt_root / "agent.md").exists():
            (prompt_root / "agent.md").write_text(_asset("fortune-agent.md"), encoding="utf-8")

    apps_store = AtomicJsonStore(root / "apps.json", [])
    apps = apps_store.read()
    if not any(item["id"] == APP_ID or item["slug"] == "fortune" for item in apps):
        apps.append(
            {
                "id": APP_ID,
                "name": "知命",
                "slug": "fortune",
                "agent_id": AGENT_ID,
                "runtime_adapter": "fortune",
                "enabled": True,
                "daily_limit": 3,
                "ttl_hours": 24,
                "max_questions": 20,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
        apps_store.write(apps)
    else:
        changed = False
        for item in apps:
            if (item["id"] == APP_ID or item["slug"] == "fortune") and "runtime_adapter" not in item:
                item["runtime_adapter"] = "fortune"
                changed = True
        if changed:
            apps_store.write(apps)
