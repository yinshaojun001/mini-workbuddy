from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.storage.collections import CollectionRepository

router = APIRouter(prefix="/api/tools", tags=["工具"])


class ToolUpdate(BaseModel):
    enabled: bool


def repo() -> CollectionRepository:
    return CollectionRepository(get_settings().workspace_dir / "tools.json")


@router.get("")
def list_tools() -> list[dict]:
    return repo().list()


@router.get("/{tool_id}")
def get_tool(tool_id: str) -> dict:
    return repo().get(tool_id)


@router.patch("/{tool_id}")
def update_tool(tool_id: str, payload: ToolUpdate) -> dict:
    return repo().update(tool_id, {"enabled": payload.enabled})

