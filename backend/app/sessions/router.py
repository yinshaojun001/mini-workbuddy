from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import get_settings
from app.storage.collections import CollectionRepository
from app.sessions.repository import SessionRepository

router = APIRouter(prefix="/api/sessions", tags=["会话"])


class SessionCreate(BaseModel):
    agent_id: str
    title: str = Field(default="新会话", min_length=1, max_length=100)


def repo() -> SessionRepository:
    return SessionRepository(get_settings().workspace_dir / "sessions")


@router.get("")
def list_sessions() -> list[dict]:
    return repo().list()


@router.post("", status_code=201)
def create_session(payload: SessionCreate) -> dict:
    CollectionRepository(get_settings().workspace_dir / "agents.json").get(payload.agent_id)
    timestamp = datetime.now(UTC).isoformat()
    return repo().create(
        {
            "id": str(uuid4()),
            "agent_id": payload.agent_id,
            "title": payload.title,
            "status": "idle",
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )


@router.get("/{session_id}")
def get_session(session_id: str) -> dict:
    return repo().get(session_id)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    repo().delete(session_id)


@router.get("/{session_id}/messages")
def list_messages(session_id: str) -> list[dict]:
    return repo().messages(session_id)

