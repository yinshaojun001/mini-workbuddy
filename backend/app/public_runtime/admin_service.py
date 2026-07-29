from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.apps.repository import AppRepository
from app.errors import AppError
from app.public_runtime.events import PublicRunEventRepository
from app.public_runtime.metrics import PublicMetricsRepository, SAFE_ERROR_CODES
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository

SESSION_STATUSES = {"active", "running", "completed", "failed", "expired"}
EVENT_TYPES = {
    "run.started",
    "agent.started",
    "model.started",
    "model.completed",
    "agent.completed",
    "run.completed",
    "model.failed",
    "agent.failed",
    "run.failed",
}
_BIRTH_FIELDS = (
    "name",
    "gender",
    "birth_date",
    "birth_time",
    "birth_time_unknown",
    "province_code",
    "city_code",
    "true_solar_time",
    "focus_topics",
)
_COUNTER_FIELDS = (
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


class PublicRunsAdminService:
    def __init__(
        self,
        sessions: PublicSessionRepository,
        events: PublicRunEventRepository,
        metrics: PublicMetricsRepository,
        quota: QuotaRepository,
        apps: AppRepository,
    ) -> None:
        self.sessions = sessions
        self.events = events
        self.metrics = metrics
        self.quota = quota
        self.apps = apps

    def list_sessions(
        self,
        *,
        app_id: str | None,
        status: str | None,
        query: str | None,
        limit: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        filters = {"app_id": app_id, "status": status, "query": query}
        anchor = self._decode_cursor(cursor, filters) if cursor else None
        apps = {item["id"]: item for item in self.apps.list()}
        items = []
        for session in self.sessions.all():
            try:
                self._canonical_session_id(str(session.get("id", "")))
            except AppError:
                continue
            if app_id and session.get("app_id") != app_id:
                continue
            session_id = str(session.get("id", ""))
            if query and query.lower() not in session_id.lower():
                continue
            try:
                summary = self._summary(session, apps.get(session.get("app_id"), {}))
            except AppError as error:
                if error.code == "PUBLIC_SESSION_NOT_FOUND":
                    continue
                raise
            except (OSError, json.JSONDecodeError):
                continue
            if status and summary["status"] != status:
                continue
            items.append(summary)

        items.sort(key=lambda item: (item["updated_at"], item["session_id"]), reverse=True)
        if anchor:
            items = [
                item
                for item in items
                if (item["updated_at"], item["session_id"]) < anchor
            ]
        page = items[:limit]
        next_cursor = None
        if len(items) > limit and page:
            last = page[-1]
            next_cursor = self._encode_cursor(
                last["updated_at"], last["session_id"], filters
            )
        return {
            "items": page,
            "next_cursor": next_cursor,
            "refreshed_at": datetime.now(UTC).isoformat(),
        }

    def detail(self, session_id: str, include_sensitive: bool) -> dict[str, Any]:
        self._canonical_session_id(session_id)
        snapshot = self.sessions.snapshot(session_id)
        session = snapshot["session"]
        app = next((item for item in self.apps.list() if item["id"] == session.get("app_id")), {})
        telemetry = self._safe_telemetry(self.events.events(session_id))
        self.sessions.get(session_id)
        kind = "dream" if snapshot["context"].get("kind") == "dream" else "fortune"
        input_fields = self._input_summary(kind, snapshot["input"], include_sensitive)
        context_summary = self._context_summary(kind, snapshot["context"])
        messages = (
            []
            if kind == "dream"
            else self._safe_messages(snapshot["messages"], snapshot["input"], include_sensitive)
        )
        result = {
            "session": self._summary(
                session,
                app,
                telemetry,
                message_count=len(snapshot["messages"]) if isinstance(snapshot["messages"], list) else 0,
            ),
            "input": {"kind": kind, "fields": input_fields},
            "context": {"kind": kind, "summary": context_summary},
            "messages": messages,
            "runs": telemetry["runs"],
            "events": telemetry["events"],
            "historical_events_unavailable": telemetry["historical_events_unavailable"],
        }
        if kind == "fortune":
            result["birth"] = input_fields
            result["chart"] = context_summary
        return result

    def stats(self) -> dict[str, Any]:
        persisted = self.metrics.store.read()
        apps = {
            app_id: self._safe_counters(counters)
            for app_id, counters in persisted.get("apps", {}).items()
            if isinstance(app_id, str) and app_id and isinstance(counters, dict)
        }
        total = self._empty_counters()
        for counters in apps.values():
            for field in _COUNTER_FIELDS:
                total[field] += counters[field]
            for error_code, count in counters["errors"].items():
                total["errors"][error_code] = total["errors"].get(error_code, 0) + count
        return {"version": 1, "apps": apps, "total": self._with_average(total)}

    def delete(self, session_id: str) -> None:
        self._canonical_session_id(session_id)
        session = self.sessions.delete_for_admin(session_id)
        if session.get("reservation_id") and not session.get("quota_committed"):
            self.quota.release(
                session["app_id"],
                session["owner_hash"],
                session["ip_hash"],
                session["reservation_id"],
            )
        self.metrics.session_deleted(session["app_id"], "admin")

    def _summary(
        self,
        session: dict[str, Any],
        app: dict[str, Any],
        telemetry: dict[str, Any] | None = None,
        message_count: int | None = None,
    ) -> dict[str, Any]:
        session_id = str(session["id"])
        telemetry = telemetry or self._safe_telemetry(self.events.events(session_id))
        if message_count is None:
            messages = self.sessions.messages(session_id)
            message_count = len(messages) if isinstance(messages, list) else 0
        max_questions = int(app.get("max_questions", 0))
        question_count = int(session.get("question_count", 0))
        last_run_status = None
        if telemetry["events"]:
            last_run_id = telemetry["events"][-1]["run_id"]
            last_run = next((run for run in telemetry["runs"] if run["run_id"] == last_run_id), None)
            last_run_status = last_run["status"] if last_run else None
        return {
            "session_id": session_id,
            "app_id": str(session.get("app_id", "")),
            "app_name": str(app.get("name") or session.get("app_id", "")),
            "status": self._status(session, max_questions),
            "created_at": str(session.get("created_at", "")),
            "updated_at": str(session.get("updated_at", "")),
            "expires_at": str(session.get("expires_at", "")),
            "remaining_questions": max(0, max_questions - question_count),
            "message_count": message_count,
            "run_count": len(telemetry["runs"]),
            "last_run_status": last_run_status,
        }

    @staticmethod
    def _status(session: dict[str, Any], max_questions: int) -> str:
        try:
            if datetime.fromisoformat(str(session["expires_at"])) <= datetime.now(UTC):
                return "expired"
        except (KeyError, TypeError, ValueError):
            pass
        internal = session.get("status")
        if internal in {"report_running", "question_running"}:
            return "running"
        if internal == "report_failed":
            return "failed"
        if internal == "report_ready" and int(session.get("question_count", 0)) >= max_questions:
            return "completed"
        return "active"

    @classmethod
    def _birth(cls, birth: dict[str, Any], include_sensitive: bool) -> dict[str, Any]:
        if include_sensitive:
            result = {field: birth.get(field) for field in _BIRTH_FIELDS}
            result["birth_time"] = cls._normalized_birth_time(birth.get("birth_time"))
            return result
        name = str(birth.get("name") or "")
        return {
            "name": (name[:1] + "*" * max(1, len(name) - 1)) if name else "***",
            "gender": "***",
            "birth_date": "****-**-**",
            "birth_time": "**:**",
            "birth_time_unknown": None,
            "province_code": "******",
            "city_code": "******",
            "true_solar_time": None,
            "focus_topics": ["***"] if birth.get("focus_topics") else [],
        }

    @staticmethod
    def _chart_summary(chart: dict[str, Any]) -> dict[str, Any]:
        pillars = chart.get("pillars") if isinstance(chart.get("pillars"), dict) else {}
        safe_pillars = {}
        for key in ("year", "month", "day", "hour"):
            pillar = pillars.get(key)
            if isinstance(pillar, dict) and isinstance(pillar.get("ganZhi"), str):
                safe_pillars[key] = {"gan_zhi": pillar["ganZhi"]}
        day_master = chart.get("day_master")
        safe_day_master = {}
        if isinstance(day_master, dict):
            gan = day_master.get("gan")
            if not isinstance(gan, str):
                gan = day_master.get("char")
            if isinstance(gan, str):
                safe_day_master["gan"] = gan
        return {"pillars": safe_pillars, "day_master": safe_day_master}

    @classmethod
    def _input_summary(
        cls,
        kind: str,
        input_data: dict[str, Any],
        include_sensitive: bool,
    ) -> dict[str, Any]:
        if kind == "fortune":
            return cls._birth(input_data, include_sensitive)
        dream_text = input_data.get("dream_text")
        recent_context = input_data.get("recent_context")
        emotions = input_data.get("emotions")
        return {
            "emotions": [item for item in emotions if isinstance(item, str)]
            if isinstance(emotions, list)
            else [],
            "recurring": input_data.get("recurring") is True,
            "dream_length": len(dream_text) if isinstance(dream_text, str) else 0,
            "has_recent_context": bool(
                isinstance(recent_context, str) and recent_context.strip()
            ),
        }

    @classmethod
    def _context_summary(cls, kind: str, context: dict[str, Any]) -> dict[str, Any]:
        if kind == "fortune":
            return cls._chart_summary(context)
        references = context.get("traditional_references")
        symbols = []
        if isinstance(references, list):
            for item in references:
                if not isinstance(item, dict):
                    continue
                symbol_id = item.get("symbol_id")
                label = item.get("label")
                if isinstance(symbol_id, str) and isinstance(label, str):
                    symbols.append({"id": symbol_id, "label": label})
        return {"symbols": symbols}

    @staticmethod
    def _safe_messages(
        messages: Any,
        birth: dict[str, Any],
        include_sensitive: bool,
    ) -> list[dict[str, Any]]:
        if not isinstance(messages, list):
            return []
        replacements = {}
        if not include_sensitive:
            stored_birth_time = str(birth.get("birth_time") or "")
            replacements = {
                str(birth.get("name") or ""): "***",
                str(birth.get("gender") or ""): "***",
                str(birth.get("birth_date") or ""): "****-**-**",
                stored_birth_time: "**:**",
                str(birth.get("province_code") or ""): "******",
                str(birth.get("city_code") or ""): "******",
            }
            normalized_birth_time = PublicRunsAdminService._normalized_birth_time(stored_birth_time)
            if normalized_birth_time:
                replacements[normalized_birth_time] = "**:**"
            for topic in birth.get("focus_topics") or []:
                if isinstance(topic, str):
                    replacements[topic] = "***"
        result = []
        for message in messages:
            if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
                continue
            content = str(message.get("content") or "")
            for private, masked in replacements.items():
                if private:
                    content = content.replace(private, masked)
            result.append(
                {
                    "id": message.get("id"),
                    "role": message.get("role"),
                    "content": content,
                    "created_at": message.get("created_at"),
                }
            )
        return result

    @staticmethod
    def _normalized_birth_time(value: Any) -> str | None:
        if value is None or value == "":
            return None
        try:
            return datetime.strptime(str(value), "%H:%M:%S").strftime("%H:%M")
        except ValueError:
            try:
                return datetime.strptime(str(value), "%H:%M").strftime("%H:%M")
            except ValueError:
                return None

    @classmethod
    def _safe_telemetry(cls, telemetry: dict[str, Any]) -> dict[str, Any]:
        events = []
        for event in telemetry.get("events", []):
            if not isinstance(event, dict):
                continue
            run_id = event.get("run_id")
            sequence = event.get("sequence")
            timestamp = event.get("timestamp")
            event_type = event.get("type")
            mode = event.get("mode")
            duration_ms = event.get("duration_ms")
            model_id = event.get("model_id")
            error_code = event.get("error_code")
            if not (
                isinstance(run_id, str)
                and 0 < len(run_id) <= 200
                and isinstance(sequence, int)
                and not isinstance(sequence, bool)
                and sequence >= 0
                and isinstance(timestamp, str)
                and cls._valid_timestamp(timestamp)
                and isinstance(event_type, str)
                and event_type in EVENT_TYPES
                and isinstance(mode, str)
                and mode in {"report", "question"}
                and isinstance(duration_ms, int)
                and not isinstance(duration_ms, bool)
                and duration_ms >= 0
                and (model_id is None or isinstance(model_id, str) and len(model_id) <= 200)
                and (
                    error_code is None
                    or isinstance(error_code, str) and error_code in SAFE_ERROR_CODES
                )
            ):
                continue
            events.append(
                {
                    "run_id": run_id,
                    "sequence": sequence,
                    "timestamp": timestamp,
                    "type": event_type,
                    "mode": mode,
                    "duration_ms": duration_ms,
                    "model_id": model_id,
                    "error_code": error_code,
                }
            )
        events.sort(key=lambda event: (event["timestamp"], event["run_id"], event["sequence"]))
        grouped: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            grouped.setdefault(event["run_id"], []).append(event)
        runs = []
        for run_id, run_events in grouped.items():
            run_events.sort(key=lambda event: (event["sequence"], event["timestamp"]))
            terminal = run_events[-1]["type"]
            status = (
                "completed"
                if terminal == "run.completed"
                else "failed"
                if terminal in {"model.failed", "agent.failed", "run.failed"}
                else "interrupted"
            )
            runs.append({"run_id": run_id, "status": status, "events": run_events})
        runs.sort(
            key=lambda run: (run["events"][-1]["timestamp"], run["run_id"]),
            reverse=True,
        )
        return {
            "events": events,
            "runs": runs,
            "historical_events_unavailable": bool(
                telemetry.get("historical_events_unavailable")
            ),
        }

    @staticmethod
    def _valid_timestamp(value: str) -> bool:
        try:
            datetime.fromisoformat(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _empty_counters() -> dict[str, Any]:
        return {**dict.fromkeys(_COUNTER_FIELDS, 0), "errors": {}}

    @classmethod
    def _safe_counters(cls, counters: dict[str, Any]) -> dict[str, Any]:
        result = cls._empty_counters()
        for field in _COUNTER_FIELDS:
            value = counters.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                result[field] = value
        errors = counters.get("errors")
        if isinstance(errors, dict):
            result["errors"] = {
                code: count
                for code, count in errors.items()
                if code in SAFE_ERROR_CODES
                and isinstance(count, int)
                and not isinstance(count, bool)
                and count >= 0
            }
        return cls._with_average(result)

    @staticmethod
    def _with_average(counters: dict[str, Any]) -> dict[str, Any]:
        result = {**counters, "errors": dict(counters["errors"])}
        completed = result["runs_completed"]
        result["average_duration_ms"] = (
            result["total_duration_ms"] / completed if completed else 0
        )
        return result

    @staticmethod
    def _canonical_session_id(session_id: str) -> None:
        try:
            if str(UUID(session_id)) != session_id:
                raise ValueError
        except (ValueError, AttributeError) as exc:
            raise AppError("PUBLIC_SESSION_NOT_FOUND", "会话不存在或已过期", 404) from exc

    @staticmethod
    def _encode_cursor(
        updated_at: str,
        session_id: str,
        filters: dict[str, Any],
    ) -> str:
        payload = json.dumps(
            {"v": 1, "updated_at": updated_at, "session_id": session_id, "filters": filters},
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return base64.urlsafe_b64encode(payload).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str, filters: dict[str, Any]) -> tuple[str, str]:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
            if not (
                isinstance(value, dict)
                and value.get("v") == 1
                and isinstance(value.get("updated_at"), str)
                and value["updated_at"]
                and isinstance(value.get("session_id"), str)
                and value["session_id"]
                and value.get("filters") == filters
            ):
                raise ValueError
            datetime.fromisoformat(value["updated_at"])
            return value["updated_at"], value["session_id"]
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise AppError("VALIDATION_ERROR", "分页游标无效", 422) from exc
