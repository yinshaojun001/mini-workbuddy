from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Callable
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.apps.repository import AppRepository
from app.config import Settings
from app.errors import AppError
from app.fortune.chart_client import ChartClient
from app.fortune.cities import resolve_city
from app.fortune.models import BirthInput
from app.public_runtime.prompt import build_system_prompt
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository
from app.runtime.approvals import ApprovalBroker
from app.runtime.engine import AgentEngine
from app.runtime.model_adapter import OpenAICompatibleAdapter
from app.storage.collections import CollectionRepository

CHINA_TZ = ZoneInfo("Asia/Shanghai")
PUBLIC_EVENTS = {"message.delta", "message.completed", "run.completed", "run.failed"}


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def public_app(settings: Settings, slug: str) -> dict:
    app = AppRepository(settings.workspace_dir / "apps.json").get_by_slug(slug)
    if not app.get("enabled"):
        raise AppError("APP_NOT_FOUND", "发布应用不存在", 404)
    return app


def repositories(settings: Settings) -> tuple[PublicSessionRepository, QuotaRepository]:
    return (
        PublicSessionRepository(settings.workspace_dir / "public_sessions"),
        QuotaRepository(settings.workspace_dir / "public_usage"),
    )


async def create_public_session(
    settings: Settings,
    app: dict,
    birth: BirthInput,
    owner_hash: str,
    ip_hash: str,
    chart_client: ChartClient,
) -> dict:
    if birth.birth_date > datetime.now(CHINA_TZ).date():
        raise AppError("INVALID_BIRTH_INPUT", "出生日期不能晚于今天", 422)
    city = resolve_city(birth.province_code, birth.city_code)
    engine_result = await chart_client.calculate(birth, city["longitude"])
    chart = {
        "input": birth.model_dump(mode="json"),
        "calculation_policy": engine_result["policy"],
        **engine_result["chart"],
        "attribution": engine_result["attribution"],
    }
    sessions, quota = repositories(settings)
    reservation_id = quota.reserve(owner_hash, ip_hash, app["daily_limit"])
    now = datetime.now(UTC)
    session = {
        "id": str(uuid4()),
        "app_id": app["id"],
        "owner_hash": owner_hash,
        "ip_hash": ip_hash,
        "status": "chart_ready",
        "reservation_id": reservation_id,
        "quota_committed": False,
        "question_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=app["ttl_hours"])).isoformat(),
    }
    try:
        sessions.create(session, birth.model_dump(mode="json"), chart)
    except Exception:
        quota.release(owner_hash, ip_hash, reservation_id)
        raise
    return session_payload(sessions, session, app)


def session_payload(sessions: PublicSessionRepository, session: dict, app: dict) -> dict:
    return {
        "session": {
            "id": session["id"],
            "status": session["status"],
            "expires_at": session["expires_at"],
            "remaining_questions": max(0, app["max_questions"] - session["question_count"]),
        },
        "chart": sessions.chart(session["id"]),
        "messages": sessions.messages(session["id"]),
    }


def owned_session(settings: Settings, app: dict, session_id: str, owner_hash: str) -> tuple[PublicSessionRepository, dict]:
    sessions, quota = repositories(settings)
    session = sessions.get_owned(session_id, owner_hash)
    if session["app_id"] != app["id"] or datetime.fromisoformat(session["expires_at"]) <= datetime.now(UTC):
        if session.get("reservation_id") and not session.get("quota_committed"):
            quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
        sessions.delete(session_id)
        raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404)
    return sessions, session


def _model_context(
    settings: Settings, app: dict, sessions: PublicSessionRepository, session: dict
) -> tuple[dict, list[dict], Path]:
    agent = CollectionRepository(settings.workspace_dir / "agents.json").get(app["agent_id"])
    model = CollectionRepository(settings.workspace_dir / "models.json").get(agent["model_id"])
    if not agent.get("enabled") or not model.get("enabled") or not model.get("api_key"):
        raise AppError("MODEL_UNAVAILABLE", "解读模型暂时不可用", 502)
    system = build_system_prompt(
        settings.workspace_dir,
        agent,
        sessions.chart(session["id"]),
        sessions.birth_input(session["id"]),
    )
    messages = [{"role": "system", "content": system}]
    messages.extend(
        {"role": item["role"], "content": item["content"]}
        for item in sessions.messages(session["id"])
        if item["role"] in {"user", "assistant"}
    )
    return model, messages, Path(agent["work_directory"])


def public_agent_stream(
    settings: Settings,
    app: dict,
    session_id: str,
    owner_hash: str,
    user_content: str,
    mode: str,
    adapter_factory: Callable[[], Any] = OpenAICompatibleAdapter,
) -> AsyncIterator[str]:
    sessions, _ = owned_session(settings, app, session_id, owner_hash)
    session = sessions.claim_run(session_id, owner_hash, mode, app["max_questions"])

    if mode == "report" and session["status"] in {"report_failed", "interrupted"}:
        _, quota = repositories(settings)
        quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
        try:
            reservation_id = quota.reserve(session["owner_hash"], session["ip_hash"], app["daily_limit"])
        except AppError:
            sessions.update(session_id, {"status": "report_failed", "updated_at": timestamp()})
            raise
        session = sessions.update(session_id, {"reservation_id": reservation_id, "updated_at": timestamp()})
    try:
        model, messages, workspace = _model_context(settings, app, sessions, session)
    except AppError:
        if mode == "report":
            _, quota = repositories(settings)
            quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
            sessions.update(session_id, {"status": "report_failed", "updated_at": timestamp()})
        raise
    messages.append({"role": "user", "content": user_content})
    sessions.update(session_id, {"updated_at": timestamp()})
    run_id = str(uuid4())
    engine = AgentEngine(adapter_factory(), ApprovalBroker(), max_rounds=2)

    async def stream() -> AsyncIterator[str]:
        sequence = 0

        def emit(event_type: str, data: dict) -> str:
            nonlocal sequence
            sequence += 1
            event = {
                "run_id": run_id,
                "sequence": sequence,
                "timestamp": timestamp(),
                "type": event_type,
                "data": data,
            }
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        yield emit("run.started", {"session_id": session_id})
        assistant_content = ""
        completed = False
        try:
            async for event in engine.run(model=model, messages=messages, tools=[], workspace=workspace):
                if event["type"] == "message.delta":
                    assistant_content += event["data"]["content"]
                if event["type"] == "run.completed":
                    completed = True
                    continue
                if event["type"] == "run.failed":
                    raise AppError(
                        event["data"].get("code", "MODEL_UNAVAILABLE"),
                        event["data"].get("message", "解读模型暂时不可用"),
                        502,
                    )
                if event["type"] in PUBLIC_EVENTS:
                    yield emit(event["type"], event["data"])
            if not completed or not assistant_content.strip():
                raise AppError("MODEL_UNAVAILABLE", "解读模型未返回有效内容", 502)

            now = timestamp()
            new_messages = []
            if mode == "question":
                new_messages.append({"id": str(uuid4()), "role": "user", "content": user_content, "created_at": now})
            new_messages.append(
                {"id": str(uuid4()), "role": "assistant", "content": assistant_content, "created_at": now}
            )
            sessions.append_messages(session_id, new_messages)
            updates = {"status": "report_ready", "updated_at": now}
            if mode == "report":
                _, quota = repositories(settings)
                quota.commit(session["owner_hash"], session["ip_hash"], session["reservation_id"])
                updates["quota_committed"] = True
            else:
                updates["question_count"] = session["question_count"] + 1
            sessions.update(session_id, updates)
            yield emit("run.completed", {})
        except asyncio.CancelledError:
            sessions.update(session_id, {"status": "interrupted", "updated_at": timestamp()})
            if mode == "report":
                _, quota = repositories(settings)
                quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
            raise
        except AppError as error:
            sessions.update(
                session_id,
                {"status": "report_failed" if mode == "report" else "report_ready", "updated_at": timestamp()},
            )
            if mode == "report":
                _, quota = repositories(settings)
                quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
            yield emit("run.failed", {"code": error.code, "message": error.message})
        except Exception:
            sessions.update(
                session_id,
                {"status": "report_failed" if mode == "report" else "report_ready", "updated_at": timestamp()},
            )
            if mode == "report":
                _, quota = repositories(settings)
                quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
            yield emit("run.failed", {"code": "MODEL_UNAVAILABLE", "message": "解读模型暂时不可用"})

    return stream()
