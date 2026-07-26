from datetime import UTC, datetime, timedelta

import pytest

from app.errors import AppError
from app.public_runtime.cleanup import cleanup_expired_sessions
from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository


def session_record(session_id: str, expires_at: datetime, status="chart_ready"):
    return {
        "id": session_id,
        "app_id": "fortune",
        "owner_hash": "owner",
        "ip_hash": "ip",
        "status": status,
        "reservation_id": "reservation",
        "quota_committed": False,
        "question_count": 0,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "expires_at": expires_at.isoformat(),
    }


def test_session_ownership_is_always_hidden_by_404(tmp_path):
    repo = PublicSessionRepository(tmp_path / "sessions")
    repo.create(session_record("one", datetime.now(UTC) + timedelta(hours=1)), {}, {})
    with pytest.raises(AppError) as error:
        repo.get_owned("one", "different-owner")
    assert error.value.status_code == 404
    assert error.value.code == "PUBLIC_SESSION_NOT_FOUND"


def test_cleanup_removes_expired_data_and_interrupts_active_runs(tmp_path):
    repo = PublicSessionRepository(tmp_path / "sessions")
    repo.create(session_record("expired", datetime.now(UTC) - timedelta(seconds=1)), {"private": True}, {})
    repo.create(
        session_record("running", datetime.now(UTC) + timedelta(hours=1), status="report_running"), {}, {}
    )
    quota = QuotaRepository(tmp_path / "usage")
    metrics = PublicMetricsRepository(tmp_path / "public_metrics.json")
    assert cleanup_expired_sessions(repo, quota, metrics) == 1
    assert not (tmp_path / "sessions" / "expired").exists()
    assert repo.get("running")["status"] == "interrupted"
    assert metrics.read()["apps"]["fortune"]["ttl_cleanups"] == 1

    assert cleanup_expired_sessions(repo, quota, metrics) == 0
    snapshot = metrics.read()
    assert snapshot["apps"]["fortune"]["ttl_cleanups"] == 1
    assert snapshot["total"]["ttl_cleanups"] == 1


def test_cleanup_continues_when_another_deleter_wins_the_race(tmp_path):
    class ConcurrentDeleteRepository(PublicSessionRepository):
        def all(self):
            sessions = super().all()
            super().delete("race-lost")
            return sessions

    repo = ConcurrentDeleteRepository(tmp_path / "sessions")
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    repo.create(session_record("race-lost", expired_at), {}, {})
    repo.create(session_record("ttl-winner", expired_at), {}, {})
    quota = QuotaRepository(tmp_path / "usage")
    metrics = PublicMetricsRepository(tmp_path / "public_metrics.json")

    assert cleanup_expired_sessions(repo, quota, metrics) == 1
    assert not (tmp_path / "sessions" / "race-lost").exists()
    assert not (tmp_path / "sessions" / "ttl-winner").exists()
    assert metrics.read()["apps"]["fortune"]["ttl_cleanups"] == 1


def test_claim_run_is_atomic_and_rejects_a_second_active_run(tmp_path):
    repo = PublicSessionRepository(tmp_path / "sessions")
    repo.create(session_record("one", datetime.now(UTC) + timedelta(hours=1)), {}, {})
    claimed = repo.claim_run("one", "owner", "report", 20)
    assert claimed["status"] == "chart_ready"
    assert repo.get("one")["status"] == "report_running"
    with pytest.raises(AppError) as error:
        repo.claim_run("one", "owner", "report", 20)
    assert error.value.code == "RUN_ALREADY_ACTIVE"
