from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.errors import AppError
from app.storage.json_store import AtomicJsonStore

CHINA_TZ = ZoneInfo("Asia/Shanghai")


class QuotaRepository:
    _lock = RLock()

    def __init__(self, root: Path, now=None) -> None:
        self.root = root
        self.now = now or (lambda: datetime.now(UTC))

    def _day(self) -> str:
        return self.now().astimezone(CHINA_TZ).date().isoformat()

    def _store(self, day: str | None = None) -> AtomicJsonStore:
        return AtomicJsonStore(self.root / f"{day or self._day()}.json", {})

    def _reservation_day(self, reservation_id: str) -> str:
        day, separator, _ = reservation_id.partition(".")
        return day if separator and len(day) == 10 else self._day()

    def _keys(self, app_id: str, visitor_hash: str, ip_hash: str) -> tuple[str, str]:
        return (
            f"app:{app_id}:visitor:{visitor_hash}",
            f"app:{app_id}:pair:{visitor_hash}:{ip_hash}",
        )

    def _active(self, record: dict, now: datetime) -> dict:
        reservations = {
            key: value
            for key, value in record.get("reservations", {}).items()
            if datetime.fromisoformat(value) > now
        }
        return {"committed": record.get("committed", 0), "reservations": reservations}

    def reserve(self, app_id: str, visitor_hash: str, ip_hash: str, limit: int) -> str:
        with self._lock:
            store = self._store()
            data = store.read()
            now = self.now()
            keys = self._keys(app_id, visitor_hash, ip_hash)
            records = {key: self._active(data.get(key, {}), now) for key in keys}
            if any(record["committed"] + len(record["reservations"]) >= limit for record in records.values()):
                raise AppError(
                    "DAILY_QUOTA_EXCEEDED",
                    f"今天的 {limit} 次测算额度已经用完",
                    429,
                    {"resets_at": self.resets_at()},
                )
            reservation_id = f"{self._day()}.{uuid4()}"
            expires_at = (now + timedelta(minutes=15)).isoformat()
            for key, record in records.items():
                record["reservations"][reservation_id] = expires_at
                data[key] = record
            store.write(data)
            return reservation_id

    def commit(self, app_id: str, visitor_hash: str, ip_hash: str, reservation_id: str) -> None:
        self._finish(app_id, visitor_hash, ip_hash, reservation_id, commit=True)

    def release(self, app_id: str, visitor_hash: str, ip_hash: str, reservation_id: str) -> None:
        self._finish(app_id, visitor_hash, ip_hash, reservation_id, commit=False)

    def _finish(
        self,
        app_id: str,
        visitor_hash: str,
        ip_hash: str,
        reservation_id: str,
        commit: bool,
    ) -> None:
        with self._lock:
            store = self._store(self._reservation_day(reservation_id))
            data = store.read()
            changed = False
            for key in self._keys(app_id, visitor_hash, ip_hash):
                record = self._active(data.get(key, {}), self.now())
                if reservation_id in record["reservations"]:
                    record["reservations"].pop(reservation_id)
                    if commit:
                        record["committed"] += 1
                    changed = True
                data[key] = record
            if changed:
                store.write(data)

    def remaining(self, app_id: str, visitor_hash: str, ip_hash: str, limit: int) -> int:
        with self._lock:
            data = self._store().read()
            now = self.now()
            used = max(
                (
                    record["committed"] + len(record["reservations"])
                    for record in (
                        self._active(data.get(key, {}), now)
                        for key in self._keys(app_id, visitor_hash, ip_hash)
                    )
                ),
                default=0,
            )
            return max(0, limit - used)

    def resets_at(self) -> str:
        local = self.now().astimezone(CHINA_TZ)
        tomorrow = (local + timedelta(days=1)).date()
        return datetime.combine(tomorrow, datetime.min.time(), CHINA_TZ).isoformat()
