from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.public_runtime.identity import COOKIE_NAME, hmac_hash, parse_token
from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.repository import PublicSessionRepository

ORIGIN = {"origin": "http://localhost:5174"}


def test_visitor_delete_counts_only_after_the_session_is_removed(client, workspace):
    settings = get_settings()
    assert client.get("/api/public/apps/fortune").status_code == 200
    visitor_id = parse_token(client.cookies.get(COOKIE_NAME), settings.public_session_secret)
    assert visitor_id is not None

    sessions = PublicSessionRepository(workspace / "public_sessions")
    now = datetime.now(UTC)
    sessions.create(
        {
            "id": "visitor-delete",
            "app_id": "fortune",
            "owner_hash": hmac_hash(visitor_id, settings.public_session_secret),
            "ip_hash": "unused",
            "status": "chart_ready",
            "reservation_id": None,
            "quota_committed": False,
            "question_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        },
        {},
        {},
    )

    path = "/api/public/apps/fortune/sessions/visitor-delete"
    assert client.delete(path, headers=ORIGIN).status_code == 204
    assert not (workspace / "public_sessions" / "visitor-delete").exists()
    metrics = PublicMetricsRepository(workspace / "public_metrics.json")
    assert metrics.read()["apps"]["fortune"]["visitor_deletions"] == 1

    assert client.delete(path, headers=ORIGIN).status_code == 404
    assert metrics.read()["apps"]["fortune"]["visitor_deletions"] == 1
