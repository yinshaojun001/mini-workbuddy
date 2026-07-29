from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.apps.repository import AppRepository
from app.config import get_settings
from app.errors import AppError
from app.storage.collections import CollectionRepository

router = APIRouter(prefix="/api/apps", tags=["发布应用"])


class AppInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=1, max_length=60)
    agent_id: str
    runtime_adapter: Literal["fortune", "dream"] = "fortune"
    enabled: bool = True
    daily_limit: int = Field(default=3, ge=1, le=20)
    ttl_hours: int = Field(default=24, ge=1, le=168)
    max_questions: int = Field(default=20, ge=0, le=100)


def repo() -> AppRepository:
    return AppRepository(get_settings().workspace_dir / "apps.json")


def validate_agent(agent_id: str) -> None:
    CollectionRepository(get_settings().workspace_dir / "agents.json").get(agent_id)


def app_health(
    item: dict,
) -> Literal[
    "ready",
    "disabled",
    "agent_unavailable",
    "model_unavailable",
    "adapter_unavailable",
    "reference_unavailable",
]:
    if not item["enabled"]:
        return "disabled"
    settings = get_settings()
    try:
        agent = CollectionRepository(settings.workspace_dir / "agents.json").get(item["agent_id"])
        model = CollectionRepository(settings.workspace_dir / "models.json").get(agent["model_id"])
    except AppError:
        return "agent_unavailable"
    if not agent.get("enabled"):
        return "agent_unavailable"
    if not model.get("enabled") or not model.get("api_key"):
        return "model_unavailable"
    return "ready"


def public_item(item: dict) -> dict:
    slug = item["slug"]
    return {
        "runtime_adapter": "fortune",
        **item,
        "health": app_health(item),
        "public_url": f"{get_settings().fortune_origin.rstrip('/')}/{slug}",
    }


@router.get("")
def list_apps() -> list[dict]:
    return [public_item(item) for item in repo().list()]


@router.get("/{app_id}")
def get_app(app_id: str) -> dict:
    return public_item(repo().get(app_id))


@router.post("", status_code=201)
def create_app(payload: AppInput) -> dict:
    validate_agent(payload.agent_id)
    timestamp = datetime.now(UTC).isoformat()
    item = {"id": str(uuid4()), **payload.model_dump(), "created_at": timestamp, "updated_at": timestamp}
    return public_item(repo().create(item))


@router.put("/{app_id}")
def update_app(app_id: str, payload: AppInput) -> dict:
    validate_agent(payload.agent_id)
    values = {**payload.model_dump(), "updated_at": datetime.now(UTC).isoformat()}
    return public_item(repo().update(app_id, values))


@router.delete("/{app_id}", status_code=204)
def delete_app(app_id: str) -> None:
    repo().delete(app_id)
