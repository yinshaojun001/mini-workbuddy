import asyncio
from contextlib import suppress
from datetime import UTC, datetime

from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository


def cleanup_expired_sessions(sessions: PublicSessionRepository, quota: QuotaRepository) -> int:
    removed = 0
    now = datetime.now(UTC)
    for session in sessions.all():
        if session["status"] in {"report_running", "question_running"}:
            sessions.update(session["id"], {"status": "interrupted"})
        if datetime.fromisoformat(session["expires_at"]) <= now:
            if session.get("reservation_id") and not session.get("quota_committed"):
                quota.release(session["owner_hash"], session["ip_hash"], session["reservation_id"])
            sessions.delete(session["id"])
            removed += 1
    return removed


async def cleanup_loop(sessions: PublicSessionRepository, quota: QuotaRepository) -> None:
    while True:
        await asyncio.sleep(15 * 60)
        cleanup_expired_sessions(sessions, quota)


async def stop_cleanup_task(task: asyncio.Task | None) -> None:
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
