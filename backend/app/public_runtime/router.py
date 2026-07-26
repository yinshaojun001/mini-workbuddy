from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.errors import AppError
from app.fortune.chart_client import ChartClient
from app.fortune.cities import city_records
from app.fortune.models import BirthInput
from app.public_runtime.identity import client_ip, hmac_hash, visitor_identity
from app.public_runtime.rate_limit import public_rate_limiter
from app.public_runtime.service import (
    create_public_session,
    owned_session,
    public_agent_stream,
    public_app,
    repositories,
    session_payload,
)
from app.runtime.model_adapter import OpenAICompatibleAdapter

router = APIRouter(prefix="/api/public/apps", tags=["公开应用"])
chart_client_factory: Callable[[], ChartClient] = lambda: ChartClient(get_settings().bazi_engine_url)
adapter_factory: Callable[[], object] = OpenAICompatibleAdapter
MAX_PUBLIC_BODY_BYTES = 16 * 1024


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=500)


def require_origin(request: Request) -> None:
    expected = get_settings().fortune_origin.rstrip("/")
    if request.headers.get("origin", "").rstrip("/") != expected:
        raise AppError("ORIGIN_NOT_ALLOWED", "请求来源不允许", 403)


def require_body_size(request: Request) -> None:
    declared = request.headers.get("content-length")
    if declared and int(declared) > MAX_PUBLIC_BODY_BYTES:
        raise AppError("REQUEST_TOO_LARGE", "请求内容不能超过 16 KB", 413)


def identities(request: Request, response: Response) -> tuple[str, str]:
    settings = get_settings()
    visitor_id = visitor_identity(request, response, settings.public_session_secret)
    return (
        hmac_hash(visitor_id, settings.public_session_secret),
        hmac_hash(client_ip(request), settings.public_ip_hash_secret),
    )


@router.get("/{slug}")
def get_public_app(slug: str, request: Request, response: Response) -> dict:
    settings = get_settings()
    app = public_app(settings, slug)
    owner_hash, ip_hash = identities(request, response)
    _, quota = repositories(settings)
    locations = [
        {key: record[key] for key in ("code", "parent_code", "name", "level")}
        for record in city_records().values()
    ]
    return {
        "name": app["name"],
        "slug": app["slug"],
        "daily_limit": app["daily_limit"],
        "ttl_hours": app["ttl_hours"],
        "max_questions": app["max_questions"],
        "locations": locations,
        "quota": {
            "remaining": quota.remaining(owner_hash, ip_hash, app["daily_limit"]),
            "resets_at": quota.resets_at(),
        },
    }


@router.post("/{slug}/sessions", status_code=201)
async def create_session(slug: str, payload: BirthInput, request: Request, response: Response) -> dict:
    require_origin(request)
    require_body_size(request)
    settings = get_settings()
    app = public_app(settings, slug)
    owner_hash, ip_hash = identities(request, response)
    public_rate_limiter.check(f"create:{ip_hash}", 5)
    result = await create_public_session(settings, app, payload, owner_hash, ip_hash, chart_client_factory())
    _, quota = repositories(settings)
    result["quota"] = {
        "daily_limit": app["daily_limit"],
        "remaining": quota.remaining(owner_hash, ip_hash, app["daily_limit"]),
        "resets_at": quota.resets_at(),
    }
    return result


@router.get("/{slug}/sessions/{session_id}")
def get_session(slug: str, session_id: str, request: Request, response: Response) -> dict:
    settings = get_settings()
    app = public_app(settings, slug)
    owner_hash, _ = identities(request, response)
    sessions, session = owned_session(settings, app, session_id, owner_hash)
    return session_payload(sessions, session, app)


@router.post("/{slug}/sessions/{session_id}/report")
def create_report(slug: str, session_id: str, request: Request, response: Response) -> StreamingResponse:
    require_origin(request)
    settings = get_settings()
    app = public_app(settings, slug)
    owner_hash, ip_hash = identities(request, response)
    public_rate_limiter.check(f"report:{ip_hash}", 5)
    stream = public_agent_stream(
        settings,
        app,
        session_id,
        owner_hash,
        "请根据可信命盘生成完整的初始解读报告。",
        "report",
        adapter_factory,
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/{slug}/sessions/{session_id}/messages")
def ask_question(
    slug: str, session_id: str, payload: QuestionInput, request: Request, response: Response
) -> StreamingResponse:
    require_origin(request)
    require_body_size(request)
    settings = get_settings()
    app = public_app(settings, slug)
    owner_hash, ip_hash = identities(request, response)
    public_rate_limiter.check(f"question:{ip_hash}", 10)
    stream = public_agent_stream(
        settings, app, session_id, owner_hash, payload.content, "question", adapter_factory
    )
    return StreamingResponse(stream, media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.delete("/{slug}/sessions/{session_id}", status_code=204)
def delete_session(slug: str, session_id: str, request: Request, response: Response) -> None:
    require_origin(request)
    settings = get_settings()
    app = public_app(settings, slug)
    owner_hash, _ = identities(request, response)
    sessions, session = owned_session(settings, app, session_id, owner_hash)
    if session.get("reservation_id") and not session.get("quota_committed"):
        _, quota = repositories(settings)
        quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
    sessions.delete(session_id, owner_hash)
