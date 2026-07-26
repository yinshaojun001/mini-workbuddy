from datetime import UTC, datetime, timedelta

import pytest

from app.errors import AppError
from app.public_runtime.quota import QuotaRepository


def test_quota_reserve_commit_release_and_expiry(tmp_path):
    current = datetime(2026, 7, 24, 2, tzinfo=UTC)
    quota = QuotaRepository(tmp_path / "usage", now=lambda: current)
    first = quota.reserve("visitor", "ip", 3)
    second = quota.reserve("visitor", "ip", 3)
    assert quota.remaining("visitor", "ip", 3) == 1
    quota.commit("visitor", "ip", first)
    quota.release("visitor", "ip", second)
    assert quota.remaining("visitor", "ip", 3) == 2

    expiring = quota.reserve("visitor", "ip", 3)
    assert expiring
    current += timedelta(minutes=16)
    assert quota.remaining("visitor", "ip", 3) == 2

    quota.reserve("visitor", "ip", 3)
    quota.reserve("visitor", "ip", 3)
    with pytest.raises(AppError) as error:
        quota.reserve("visitor", "ip", 3)
    assert error.value.code == "DAILY_QUOTA_EXCEEDED"
    assert error.value.details["resets_at"].endswith("+08:00")


def test_quota_commits_to_the_reservation_day_across_midnight(tmp_path):
    current = datetime(2026, 7, 24, 15, 59, tzinfo=UTC)
    quota = QuotaRepository(tmp_path / "usage", now=lambda: current)
    reservation = quota.reserve("visitor", "ip", 3)
    assert reservation.startswith("2026-07-24.")
    current += timedelta(minutes=2)
    quota.commit("visitor", "ip", reservation)
    previous_day = (tmp_path / "usage" / "2026-07-24.json").read_text(encoding="utf-8")
    assert '"committed": 1' in previous_day
