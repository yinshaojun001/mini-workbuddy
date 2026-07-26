import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.public_runtime.metrics import PublicMetricsRepository


EMPTY_COUNTERS = {
    "sessions_created": 0,
    "reports_completed": 0,
    "reports_failed": 0,
    "questions_completed": 0,
    "questions_failed": 0,
    "runs_started": 0,
    "runs_completed": 0,
    "total_duration_ms": 0,
    "admin_deletions": 0,
    "visitor_deletions": 0,
    "ttl_cleanups": 0,
    "errors": {},
}


def test_metrics_start_with_a_versioned_empty_document(tmp_path):
    path = tmp_path / "public_metrics.json"
    metrics = PublicMetricsRepository(path)

    assert metrics.read() == {
        "version": 1,
        "apps": {},
        "total": {**EMPTY_COUNTERS, "average_duration_ms": 0},
    }
    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 1, "apps": {}}


def test_lifecycle_methods_update_only_their_semantic_counters(tmp_path):
    path = tmp_path / "public_metrics.json"
    metrics = PublicMetricsRepository(path)

    metrics.session_created("fortune")
    metrics.run_started("fortune")
    metrics.run_completed("fortune", "report", 120)
    metrics.run_started("fortune")
    metrics.run_completed("fortune", "question", 80)
    metrics.run_started("fortune")
    metrics.run_failed("fortune", "report", "MODEL_TIMEOUT")
    metrics.run_started("fortune")
    metrics.run_failed("fortune", "question", "MODEL_RATE_LIMITED")
    metrics.session_deleted("fortune", "admin")
    metrics.session_deleted("fortune", "visitor")
    metrics.session_deleted("fortune", "ttl")

    app = metrics.read()["apps"]["fortune"]
    assert app == {
        "sessions_created": 1,
        "reports_completed": 1,
        "reports_failed": 1,
        "questions_completed": 1,
        "questions_failed": 1,
        "runs_started": 4,
        "runs_completed": 2,
        "total_duration_ms": 200,
        "admin_deletions": 1,
        "visitor_deletions": 1,
        "ttl_cleanups": 1,
        "errors": {"MODEL_RATE_LIMITED": 1, "MODEL_TIMEOUT": 1},
        "average_duration_ms": 100,
    }

    persisted = json.loads(path.read_text(encoding="utf-8"))["apps"]["fortune"]
    assert "average_duration_ms" not in persisted
    assert "total" not in json.loads(path.read_text(encoding="utf-8"))


def test_read_derives_cross_app_totals_and_average_from_successful_runs(tmp_path):
    metrics = PublicMetricsRepository(tmp_path / "public_metrics.json")
    metrics.run_completed("fortune", "report", 100)
    metrics.run_completed("assistant", "question", 50)
    metrics.run_failed("assistant", "question", "ENGINE_FAILED")

    snapshot = metrics.read()
    assert snapshot["apps"]["fortune"]["average_duration_ms"] == 100
    assert snapshot["apps"]["assistant"]["average_duration_ms"] == 50
    assert snapshot["total"] == {
        **EMPTY_COUNTERS,
        "reports_completed": 1,
        "questions_completed": 1,
        "questions_failed": 1,
        "runs_completed": 2,
        "total_duration_ms": 150,
        "errors": {"ENGINE_FAILED": 1},
        "average_duration_ms": 75,
    }


def test_zero_successful_runs_have_zero_average_duration(tmp_path):
    metrics = PublicMetricsRepository(tmp_path / "public_metrics.json")
    metrics.run_failed("fortune", "report", "MODEL_RESPONSE_INVALID")

    snapshot = metrics.read()
    assert snapshot["apps"]["fortune"]["average_duration_ms"] == 0
    assert snapshot["total"]["average_duration_ms"] == 0


def test_multiple_repository_instances_do_not_lose_concurrent_updates(tmp_path):
    path = tmp_path / "public_metrics.json"
    repositories = [PublicMetricsRepository(path) for _ in range(8)]

    def increment(index: int) -> None:
        repositories[index % len(repositories)].session_created("fortune")

    with ThreadPoolExecutor(max_workers=12) as executor:
        list(executor.map(increment, range(400)))

    assert PublicMetricsRepository(path).read()["apps"]["fortune"]["sessions_created"] == 400


@pytest.mark.parametrize("mode", ["", "REPORT", "tool", "session_id"])
def test_invalid_run_modes_are_rejected_without_changing_the_file(tmp_path, mode):
    path = tmp_path / "public_metrics.json"
    metrics = PublicMetricsRepository(path)
    before = metrics.read()

    with pytest.raises(ValueError, match="mode"):
        metrics.run_completed("fortune", mode, 10)
    with pytest.raises(ValueError, match="mode"):
        metrics.run_failed("fortune", mode, "ENGINE_FAILED")

    assert metrics.read() == before


@pytest.mark.parametrize(
    "error_code",
    ["", "DEEPSEEK_SAID_BAD_KEY", "SESSION_EXPIRED", "MODEL_TIMEOUT: secret", "pub_123"],
)
def test_unsafe_error_codes_are_rejected_without_creating_dynamic_fields(tmp_path, error_code):
    path = tmp_path / "public_metrics.json"
    metrics = PublicMetricsRepository(path)
    before = metrics.read()

    with pytest.raises(ValueError, match="error code"):
        metrics.run_failed("fortune", "report", error_code)

    assert metrics.read() == before


@pytest.mark.parametrize("cause", ["", "administrator", "expired", "pub_123"])
def test_invalid_deletion_causes_are_rejected_without_changing_the_file(tmp_path, cause):
    path = tmp_path / "public_metrics.json"
    metrics = PublicMetricsRepository(path)
    before = metrics.read()

    with pytest.raises(ValueError, match="deletion cause"):
        metrics.session_deleted("fortune", cause)

    assert metrics.read() == before


@pytest.mark.parametrize("duration_ms", [-1, 1.2, float("inf"), True])
def test_invalid_durations_are_rejected(tmp_path, duration_ms):
    metrics = PublicMetricsRepository(tmp_path / "public_metrics.json")

    with pytest.raises(ValueError, match="duration"):
        metrics.run_completed("fortune", "report", duration_ms)


def test_persisted_metrics_contain_only_aggregate_fields(tmp_path):
    path = tmp_path / "public_metrics.json"
    metrics = PublicMetricsRepository(path)
    metrics.session_created("fortune")
    metrics.run_failed("fortune", "report", "MODEL_AUTH_FAILED")

    persisted = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(persisted).lower()
    prohibited = (
        "session_id",
        "message",
        "birth",
        "owner",
        "cookie",
        "ip_hash",
        "visitor_hash",
        "api_key",
        "prompt",
    )
    assert all(term not in serialized for term in prohibited)
    assert set(persisted) == {"version", "apps"}
    assert set(persisted["apps"]["fortune"]) == set(EMPTY_COUNTERS)
