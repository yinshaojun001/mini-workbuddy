from pathlib import Path
from typing import Any

from app.errors import AppError
from app.storage.json_store import AtomicJsonStore


class CollectionRepository:
    def __init__(self, path: Path) -> None:
        self.store = AtomicJsonStore(path, [])

    def list(self) -> list[dict[str, Any]]:
        return self.store.read()

    def get(self, item_id: str) -> dict[str, Any]:
        item = next((item for item in self.list() if item["id"] == item_id), None)
        if item is None:
            raise AppError("NOT_FOUND", "资源不存在", 404)
        return item

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        items = self.list()
        items.append(item)
        self.store.write(items)
        return item

    def update(self, item_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        items = self.list()
        for index, item in enumerate(items):
            if item["id"] == item_id:
                items[index] = {**item, **updates, "id": item_id}
                self.store.write(items)
                return items[index]
        raise AppError("NOT_FOUND", "资源不存在", 404)

    def delete(self, item_id: str) -> None:
        items = self.list()
        filtered = [item for item in items if item["id"] != item_id]
        if len(filtered) == len(items):
            raise AppError("NOT_FOUND", "资源不存在", 404)
        self.store.write(filtered)

