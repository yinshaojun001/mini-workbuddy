import asyncio
from contextlib import suppress
from datetime import UTC, datetime

from app.errors import AppError
from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository


def cleanup_expired_sessions(
    sessions: PublicSessionRepository,
    quota: QuotaRepository,
    metrics: PublicMetricsRepository,
) -> int:
    removed = 0
    now = datetime.now(UTC)
    for session in sessions.all():
        if session["status"] in {"report_running", "question_running"}:
            try:
                sessions.update(session["id"], {"status": "interrupted"})
            except AppError as error:
                if error.code == "PUBLIC_SESSION_NOT_FOUND":
                    continue
                raise
        if datetime.fromisoformat(session["expires_at"]) <= now:
            if session.get("reservation_id") and not session.get("quota_committed"):
                quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
            try:
                sessions.delete(session["id"])
            except AppError as error:
                if error.code == "PUBLIC_SESSION_NOT_FOUND":
                    continue
                raise
            metrics.session_deleted(session["app_id"], "ttl")
            removed += 1
    return removed


async def cleanup_loop(
    sessions: PublicSessionRepository,
    quota: QuotaRepository,
    metrics: PublicMetricsRepository,
) -> None:
    while True:
        await asyncio.sleep(15 * 60)
        cleanup_expired_sessions(sessions, quota, metrics)


async def stop_cleanup_task(task: asyncio.Task | None) -> None:
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
