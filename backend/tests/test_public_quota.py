from datetime import UTC, datetime, timedelta

import pytest

from app.errors import AppError
from app.public_runtime.quota import QuotaRepository


def test_quota_reserve_commit_release_and_expiry(tmp_path):
    current = datetime(2026, 7, 24, 2, tzinfo=UTC)
    quota = QuotaRepository(tmp_path / "usage", now=lambda: current)
    first = quota.reserve("fortune", "visitor", "ip", 3)
    second = quota.reserve("fortune", "visitor", "ip", 3)
    assert quota.remaining("fortune", "visitor", "ip", 3) == 1
    quota.commit("fortune", "visitor", "ip", first)
    quota.release("fortune", "visitor", "ip", second)
    assert quota.remaining("fortune", "visitor", "ip", 3) == 2

    expiring = quota.reserve("fortune", "visitor", "ip", 3)
    assert expiring
    current += timedelta(minutes=16)
    assert quota.remaining("fortune", "visitor", "ip", 3) == 2

    quota.reserve("fortune", "visitor", "ip", 3)
    quota.reserve("fortune", "visitor", "ip", 3)
    with pytest.raises(AppError) as error:
        quota.reserve("fortune", "visitor", "ip", 3)
    assert error.value.code == "DAILY_QUOTA_EXCEEDED"
    assert error.value.details["resets_at"].endswith("+08:00")


def test_quota_commits_to_the_reservation_day_across_midnight(tmp_path):
    current = datetime(2026, 7, 24, 15, 59, tzinfo=UTC)
    quota = QuotaRepository(tmp_path / "usage", now=lambda: current)
    reservation = quota.reserve("fortune", "visitor", "ip", 3)
    assert reservation.startswith("2026-07-24.")
    current += timedelta(minutes=2)
    quota.commit("fortune", "visitor", "ip", reservation)
    previous_day = (tmp_path / "usage" / "2026-07-24.json").read_text(encoding="utf-8")
    assert '"committed": 1' in previous_day


def test_quota_is_scoped_by_app_id(tmp_path):
    quota = QuotaRepository(tmp_path / "usage")
    for _ in range(3):
        reservation = quota.reserve("fortune", "visitor", "ip", 3)
        quota.commit("fortune", "visitor", "ip", reservation)

    assert quota.remaining("fortune", "visitor", "ip", 3) == 0
    assert quota.remaining("dream", "visitor", "ip", 3) == 3
