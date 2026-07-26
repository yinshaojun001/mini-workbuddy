from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any

from app.storage.json_store import AtomicJsonStore

METRICS_VERSION = 1
RUN_MODES = frozenset({"report", "question"})
SAFE_ERROR_CODES = frozenset(
    {
        "MODEL_TIMEOUT",
        "MODEL_AUTH_FAILED",
        "MODEL_RATE_LIMITED",
        "MODEL_RESPONSE_INVALID",
        "ENGINE_FAILED",
    }
)
DELETION_CAUSES = frozenset({"admin", "visitor", "ttl"})

_COUNTER_NAMES = (
    "sessions_created",
    "reports_completed",
    "reports_failed",
    "questions_completed",
    "questions_failed",
    "runs_started",
    "runs_completed",
    "total_duration_ms",
    "admin_deletions",
    "visitor_deletions",
    "ttl_cleanups",
)


def _empty_counters() -> dict[str, Any]:
    return {**dict.fromkeys(_COUNTER_NAMES, 0), "errors": {}}


class PublicMetricsRepository:
    _lock = RLock()

    def __init__(self, path: Path) -> None:
        self.store = AtomicJsonStore(path, {"version": METRICS_VERSION, "apps": {}})

    def session_created(self, app_id: str) -> None:
        self._update(app_id, lambda counters: self._increment(counters, "sessions_created"))

    def run_started(self, app_id: str) -> None:
        self._update(app_id, lambda counters: self._increment(counters, "runs_started"))

    def run_completed(self, app_id: str, mode: str, duration_ms: int) -> None:
        self._validate_mode(mode)
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms < 0:
            raise ValueError("duration_ms must be a non-negative integer")

        def update(counters: dict[str, Any]) -> None:
            self._increment(counters, f"{mode}s_completed")
            self._increment(counters, "runs_completed")
            counters["total_duration_ms"] += duration_ms

        self._update(app_id, update)

    def run_failed(self, app_id: str, mode: str, error_code: str) -> None:
        self._validate_mode(mode)
        if error_code not in SAFE_ERROR_CODES:
            raise ValueError("error code is not in the safe metrics allowlist")

        def update(counters: dict[str, Any]) -> None:
            self._increment(counters, f"{mode}s_failed")
            errors = counters["errors"]
            errors[error_code] = errors.get(error_code, 0) + 1

        self._update(app_id, update)

    def session_deleted(self, app_id: str, cause: str) -> None:
        if cause not in DELETION_CAUSES:
            raise ValueError("deletion cause must be admin, visitor, or ttl")
        field = "ttl_cleanups" if cause == "ttl" else f"{cause}_deletions"
        self._update(app_id, lambda counters: self._increment(counters, field))

    def read(self) -> dict[str, Any]:
        with self._lock:
            persisted = self.store.read()

        apps = {
            app_id: self._with_average(self._normalized_counters(counters))
            for app_id, counters in persisted.get("apps", {}).items()
        }
        total = _empty_counters()
        for counters in apps.values():
            for field in _COUNTER_NAMES:
                total[field] += counters[field]
            for error_code, count in counters["errors"].items():
                total["errors"][error_code] = total["errors"].get(error_code, 0) + count

        return {
            "version": METRICS_VERSION,
            "apps": apps,
            "total": self._with_average(total),
        }

    def _update(self, app_id: str, operation: Callable[[dict[str, Any]], None]) -> None:
        if not isinstance(app_id, str) or not app_id:
            raise ValueError("app_id must be a non-empty string")
        with self._lock:
            data = self.store.read()
            apps = data.setdefault("apps", {})
            counters = self._normalized_counters(apps.get(app_id, {}))
            operation(counters)
            apps[app_id] = counters
            data["version"] = METRICS_VERSION
            self.store.write(data)

    @staticmethod
    def _increment(counters: dict[str, Any], field: str) -> None:
        counters[field] += 1

    @staticmethod
    def _validate_mode(mode: str) -> None:
        if mode not in RUN_MODES:
            raise ValueError("mode must be report or question")

    @staticmethod
    def _normalized_counters(value: dict[str, Any]) -> dict[str, Any]:
        counters = _empty_counters()
        for field in _COUNTER_NAMES:
            counters[field] = value.get(field, 0)
        counters["errors"] = deepcopy(value.get("errors", {}))
        return counters

    @staticmethod
    def _with_average(counters: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(counters)
        completed = result["runs_completed"]
        result["average_duration_ms"] = result["total_duration_ms"] / completed if completed else 0
        return result
