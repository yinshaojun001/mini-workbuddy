from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl

from app.config import get_settings
from app.errors import AppError
from app.storage.collections import CollectionRepository

router = APIRouter(prefix="/api/models", tags=["模型"])


class ModelInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    provider: Literal["deepseek", "qwen"]
    model: str = Field(min_length=1, max_length=120)
    base_url: HttpUrl
    api_key: str = ""
    enabled: bool = True
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=131072)


def repo() -> CollectionRepository:
    return CollectionRepository(get_settings().workspace_dir / "models.json")


def public_model(item: dict) -> dict:
    key = item.get("api_key", "")
    return {
        **{key_name: value for key_name, value in item.items() if key_name != "api_key"},
        "has_api_key": bool(key),
        "api_key_hint": f"••••{key[-4:]}" if key else "",
    }


@router.get("")
def list_models() -> list[dict]:
    return [public_model(item) for item in repo().list()]


@router.get("/{model_id}")
def get_model(model_id: str) -> dict:
    return public_model(repo().get(model_id))


@router.post("", status_code=201)
def create_model(payload: ModelInput) -> dict:
    timestamp = datetime.now(UTC).isoformat()
    item = {
        "id": str(uuid4()),
        **payload.model_dump(mode="json"),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    return public_model(repo().create(item))


@router.put("/{model_id}")
def update_model(model_id: str, payload: ModelInput) -> dict:
    current = repo().get(model_id)
    values = payload.model_dump(mode="json")
    if not values["api_key"]:
        values["api_key"] = current.get("api_key", "")
    values["updated_at"] = datetime.now(UTC).isoformat()
    return public_model(repo().update(model_id, values))


@router.delete("/{model_id}", status_code=204)
def delete_model(model_id: str) -> None:
    agents = CollectionRepository(get_settings().workspace_dir / "agents.json").list()
    if any(agent.get("model_id") == model_id for agent in agents):
        raise AppError("MODEL_IN_USE", "该模型仍被智能体使用", 409)
    repo().delete(model_id)


@router.post("/{model_id}/test")
async def test_model(model_id: str) -> dict:
    model = repo().get(model_id)
    if not model.get("api_key"):
        raise AppError("MODEL_API_KEY_MISSING", "请先填写 API Key", 422)
    url = model["base_url"].rstrip("/") + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {model['api_key']}"},
                json={
                    "model": model["model"],
                    "messages": [{"role": "user", "content": "回复 OK"}],
                    "max_tokens": 4,
                    "stream": False,
                },
            )
        if response.status_code == 401:
            raise AppError("MODEL_AUTH_FAILED", "模型鉴权失败", 400)
        if response.status_code == 429:
            raise AppError("MODEL_RATE_LIMITED", "模型请求达到限流", 400)
        response.raise_for_status()
        response.json()
    except AppError:
        raise
    except httpx.TimeoutException as exc:
        raise AppError("MODEL_TIMEOUT", "模型连接超时", 400) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError("MODEL_CONNECTION_FAILED", "模型连接失败", 400) from exc
    return {"success": True, "message": "模型连接正常"}

