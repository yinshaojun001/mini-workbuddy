from collections.abc import Sequence

from app.errors import AppError
from app.public_runtime.adapters.base import PublicAppAdapter


class PublicAdapterRegistry:
    def __init__(self, adapters: list[PublicAppAdapter]):
        self._items = {adapter.id: adapter for adapter in adapters}
        if len(self._items) != len(adapters):
            raise ValueError("duplicate public adapter id")

    def get(self, adapter_id: str) -> PublicAppAdapter:
        try:
            return self._items[adapter_id]
        except KeyError as exc:
            raise AppError("APP_ADAPTER_NOT_FOUND", "发布应用暂不可用", 503) from exc

    def ids(self) -> Sequence[str]:
        return tuple(sorted(self._items))
