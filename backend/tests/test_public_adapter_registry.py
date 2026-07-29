import pytest

from app.errors import AppError
from app.public_runtime.adapters.registry import PublicAdapterRegistry


class FakeAdapter:
    def __init__(self, adapter_id: str):
        self.id = adapter_id


def test_registry_returns_registered_adapter_and_sorted_ids():
    dream = FakeAdapter("dream")
    fortune = FakeAdapter("fortune")
    registry = PublicAdapterRegistry([fortune, dream])

    assert registry.get("dream") is dream
    assert registry.ids() == ("dream", "fortune")


def test_registry_rejects_duplicate_and_unknown_adapter_ids():
    with pytest.raises(ValueError, match="duplicate public adapter id"):
        PublicAdapterRegistry([FakeAdapter("fortune"), FakeAdapter("fortune")])

    with pytest.raises(AppError) as captured:
        PublicAdapterRegistry([]).get("missing")
    assert captured.value.code == "APP_ADAPTER_NOT_FOUND"
    assert captured.value.status_code == 503
