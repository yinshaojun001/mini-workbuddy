from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

from app.errors import AppError
from app.storage.json_store import AtomicJsonStore


class AppRepository:
    _lock = RLock()

    def __init__(self, path: Path) -> None:
        self.store = AtomicJsonStore(path, [])

    def list(self) -> list[dict[str, Any]]:
        return self.store.read()

    def get(self, app_id: str) -> dict[str, Any]:
        item = next((item for item in self.list() if item["id"] == app_id), None)
        if item is None:
            raise AppError("APP_NOT_FOUND", "发布应用不存在", 404)
        return item

    def get_by_slug(self, slug: str) -> dict[str, Any]:
        item = next((item for item in self.list() if item["slug"] == slug), None)
        if item is None:
            raise AppError("APP_NOT_FOUND", "发布应用不存在", 404)
        return item

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            items = self.list()
            if any(existing["slug"] == item["slug"] for existing in items):
                raise AppError("APP_SLUG_EXISTS", "Slug 已存在", 409)
            items.append(item)
            self.store.write(items)
        return item

    def update(self, app_id: str, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            items = self.list()
            if any(item["slug"] == values["slug"] and item["id"] != app_id for item in items):
                raise AppError("APP_SLUG_EXISTS", "Slug 已存在", 409)
            for index, item in enumerate(items):
                if item["id"] == app_id:
                    items[index] = {**item, **values, "id": app_id}
                    self.store.write(items)
                    return items[index]
        raise AppError("APP_NOT_FOUND", "发布应用不存在", 404)

    def delete(self, app_id: str) -> None:
        with self._lock:
            items = self.list()
            filtered = [item for item in items if item["id"] != app_id]
            if len(filtered) == len(items):
                raise AppError("APP_NOT_FOUND", "发布应用不存在", 404)
            self.store.write(filtered)
