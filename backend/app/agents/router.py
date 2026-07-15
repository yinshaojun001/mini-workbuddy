from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.errors import AppError
from app.skills.router import get_metadata
from app.storage.collections import CollectionRepository

router = APIRouter(prefix="/api/agents", tags=["智能体"])


class AgentInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    model_id: str
    tool_ids: list[str] = []
    skill_ids: list[str] = []
    work_directory: str = ""
    enabled: bool = True


class PromptInput(BaseModel):
    content: str


def repo() -> CollectionRepository:
    return CollectionRepository(get_settings().workspace_dir / "agents.json")


def validate(payload: AgentInput, agent_id: str | None = None) -> None:
    models = CollectionRepository(get_settings().workspace_dir / "models.json").list()
    if not any(model["id"] == payload.model_id for model in models):
        raise AppError("MODEL_NOT_FOUND", "所选模型不存在", 422)
    tools = CollectionRepository(get_settings().workspace_dir / "tools.json").list()
    enabled_tools = {tool["id"] for tool in tools if tool["enabled"]}
    if not set(payload.tool_ids).issubset(enabled_tools):
        raise AppError("INVALID_TOOL_BINDING", "包含不存在或已停用的工具", 422)
    for skill_id in payload.skill_ids:
        if not get_metadata(skill_id)["enabled"]:
            raise AppError("INVALID_SKILL_BINDING", "包含已停用的技能", 422)
    if any(item["name"] == payload.name and item["id"] != agent_id for item in repo().list()):
        raise AppError("AGENT_NAME_EXISTS", "智能体名称已存在", 409)


def resolved_work_directory(agent_id: str, requested: str) -> str:
    path = Path(requested).expanduser() if requested.strip() else get_settings().workspace_dir / "runtime" / agent_id
    path = path.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@router.get("")
def list_agents() -> list[dict]:
    return repo().list()


@router.get("/{agent_id}")
def get_agent(agent_id: str) -> dict:
    return repo().get(agent_id)


@router.post("", status_code=201)
def create_agent(payload: AgentInput) -> dict:
    validate(payload)
    agent_id = str(uuid4())
    timestamp = datetime.now(UTC).isoformat()
    item = {
        "id": agent_id,
        **payload.model_dump(),
        "work_directory": resolved_work_directory(agent_id, payload.work_directory),
        "is_builtin": False,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    prompt_dir = get_settings().workspace_dir / "agents" / agent_id
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "agent.md").write_text("# 系统提示词\n\n", encoding="utf-8")
    return repo().create(item)


@router.put("/{agent_id}")
def update_agent(agent_id: str, payload: AgentInput) -> dict:
    current = repo().get(agent_id)
    validate(payload, agent_id)
    values = payload.model_dump()
    values["work_directory"] = resolved_work_directory(agent_id, payload.work_directory)
    values["updated_at"] = datetime.now(UTC).isoformat()
    values["is_builtin"] = current["is_builtin"]
    return repo().update(agent_id, values)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: str) -> None:
    agent = repo().get(agent_id)
    if agent.get("is_builtin"):
        raise AppError("BUILTIN_AGENT", "主 Agent 不可删除", 409)
    repo().delete(agent_id)


@router.get("/{agent_id}/prompt")
def get_prompt(agent_id: str) -> dict[str, str]:
    repo().get(agent_id)
    path = get_settings().workspace_dir / "agents" / agent_id / "agent.md"
    return {"content": path.read_text(encoding="utf-8")}


@router.put("/{agent_id}/prompt")
def update_prompt(agent_id: str, payload: PromptInput) -> dict[str, str]:
    repo().get(agent_id)
    path = get_settings().workspace_dir / "agents" / agent_id / "agent.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content, encoding="utf-8")
    return {"content": payload.content}

