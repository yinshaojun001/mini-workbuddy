import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.errors import AppError
from app.runs.repository import RunRepository
from app.runtime.approvals import ApprovalBroker
from app.runtime.engine import AgentEngine
from app.runtime.model_adapter import OpenAICompatibleAdapter
from app.sessions.repository import SessionRepository
from app.skills.router import get_metadata
from app.storage.collections import CollectionRepository

router = APIRouter(prefix="/api", tags=["运行时"])
approval_broker = ApprovalBroker()


class RunInput(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)


class ApprovalInput(BaseModel):
    allowed: bool


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def build_context(session: dict[str, Any]) -> tuple[dict, list[dict], list[dict], Path]:
    settings = get_settings()
    agent = CollectionRepository(settings.workspace_dir / "agents.json").get(session["agent_id"])
    if not agent["enabled"]:
        raise AppError("AGENT_DISABLED", "智能体已停用", 422)
    model = CollectionRepository(settings.workspace_dir / "models.json").get(agent["model_id"])
    tools = [
        tool
        for tool in CollectionRepository(settings.workspace_dir / "tools.json").list()
        if tool["id"] in agent["tool_ids"] and tool["enabled"]
    ]
    prompt = (settings.workspace_dir / "agents" / agent["id"] / "agent.md").read_text(encoding="utf-8")
    skill_blocks = []
    for skill_id in agent["skill_ids"]:
        metadata = get_metadata(skill_id)
        if metadata["enabled"]:
            content = (settings.workspace_dir / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8")
            skill_blocks.append(f"## 技能：{metadata['name']}\n\n{content}")
    system = prompt
    if skill_blocks:
        system += "\n\n# 可用技能\n\n" + "\n\n---\n\n".join(skill_blocks)
    messages = [{"role": "system", "content": system}]
    return model, messages, tools, Path(agent["work_directory"])


@router.post("/sessions/{session_id}/runs")
def start_run(session_id: str, payload: RunInput) -> StreamingResponse:
    settings = get_settings()
    sessions = SessionRepository(settings.workspace_dir / "sessions")
    session = sessions.get(session_id)
    run_id = str(uuid4())
    runs = RunRepository(settings.workspace_dir / "runs")
    model, messages, tools, workspace = build_context(session)
    existing = sessions.messages(session_id)
    messages.extend({"role": item["role"], "content": item["content"]} for item in existing if item["role"] in {"user", "assistant"})
    user_message = {"id": str(uuid4()), "role": "user", "content": payload.content, "created_at": timestamp()}
    sessions.append_message(session_id, user_message)
    messages.append({"role": "user", "content": payload.content})
    engine = AgentEngine(OpenAICompatibleAdapter(), approval_broker, settings.max_tool_rounds)

    async def stream():
        sequence = 0

        async def emit(event_type: str, data: dict) -> str:
            nonlocal sequence
            sequence += 1
            event = {"run_id": run_id, "sequence": sequence, "timestamp": timestamp(), "type": event_type, "data": data}
            runs.append(run_id, event)
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        yield await emit("run.started", {"session_id": session_id, "agent_id": session["agent_id"]})
        assistant_content = ""
        try:
            async for event in engine.run(model=model, messages=messages, tools=tools, workspace=workspace):
                if event["type"] == "message.delta":
                    assistant_content += event["data"]["content"]
                yield await emit(event["type"], event["data"])
            if assistant_content:
                sessions.append_message(
                    session_id,
                    {"id": str(uuid4()), "role": "assistant", "content": assistant_content, "created_at": timestamp()},
                )
        except AppError as error:
            yield await emit("run.failed", {"code": error.code, "message": error.message})
        except Exception:
            yield await emit("run.failed", {"code": "INTERNAL_ERROR", "message": "运行时发生未知错误"})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Run-ID": run_id})


@router.post("/approvals/{approval_id}")
def resolve_approval(approval_id: str, payload: ApprovalInput) -> dict:
    approval_broker.resolve(approval_id, payload.allowed)
    return {"id": approval_id, "allowed": payload.allowed}

