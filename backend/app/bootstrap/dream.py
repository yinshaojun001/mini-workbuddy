from datetime import UTC, datetime
from pathlib import Path

from app.storage.json_store import AtomicJsonStore

SKILL_ID = "dream-interpreter"
AGENT_ID = "dream-analysis-agent"
APP_ID = "dream"


def _asset(name: str) -> str:
    return (Path(__file__).parent / "assets" / name).read_text(encoding="utf-8")


def bootstrap_dream_agent(root: Path) -> None:
    timestamp = datetime.now(UTC).isoformat()
    skill_root = root / "skills" / SKILL_ID
    skill_root.mkdir(parents=True, exist_ok=True)
    skill_path = skill_root / "SKILL.md"
    if not skill_path.exists():
        skill_path.write_text(_asset("dream-interpreter/SKILL.md"), encoding="utf-8")
    metadata_path = skill_root / "metadata.json"
    if not metadata_path.exists():
        AtomicJsonStore(metadata_path, {}).write(
            {
                "id": SKILL_ID,
                "name": "融合型梦境解读",
                "description": "传统文化参照与现代心理反思的克制型解梦规范",
                "enabled": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

    prompt_root = root / "agents" / AGENT_ID
    prompt_root.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_root / "agent.md"
    if not prompt_path.exists():
        prompt_path.write_text(_asset("dream-agent.md"), encoding="utf-8")

    agents_store = AtomicJsonStore(root / "agents.json", [])
    agents = agents_store.read()
    if any(item["id"] == AGENT_ID for item in agents):
        return

    work_directory = root / "runtime" / AGENT_ID
    work_directory.mkdir(parents=True, exist_ok=True)
    agents.append(
        {
            "id": AGENT_ID,
            "name": "知梦解梦 Agent",
            "description": "知梦公开应用的固定融合型解梦 Agent",
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


def bootstrap_dream_app(root: Path) -> None:
    timestamp = datetime.now(UTC).isoformat()
    apps_store = AtomicJsonStore(root / "apps.json", [])
    apps = apps_store.read()
    if any(item["id"] == APP_ID or item["slug"] == APP_ID for item in apps):
        return
    apps.append(
        {
            "id": APP_ID,
            "name": "知梦",
            "slug": "dream",
            "agent_id": AGENT_ID,
            "runtime_adapter": "dream",
            "enabled": False,
            "daily_limit": 3,
            "ttl_hours": 24,
            "max_questions": 20,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )
    apps_store.write(apps)
