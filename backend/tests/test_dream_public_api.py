import json

from fastapi.testclient import TestClient

from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.repository import PublicSessionRepository
from app.storage.json_store import AtomicJsonStore
from tests.test_dream_public_adapter import dream_payload, reference_path
from tests.test_public_runtime_api import ORIGIN, RecordingAdapter, enable_model


def enable_dream_app(workspace):
    store = AtomicJsonStore(workspace / "apps.json", [])
    apps = store.read()
    dream = next(item for item in apps if item["id"] == "dream")
    dream["enabled"] = True
    store.write(apps)


def configure_dream_fakes(monkeypatch, workspace):
    from app.public_runtime import router
    from app.config import get_settings
    from app.public_runtime.adapters.dream import DreamPublicAdapter
    from app.public_runtime.adapters.fortune import FortunePublicAdapter
    from app.public_runtime.adapters.registry import (
        PublicAdapterRegistry,
        configure_public_adapter_registry,
    )
    from tests.test_public_runtime_api import FakeChartClient

    enable_model(workspace)
    enable_dream_app(workspace)
    RecordingAdapter.calls.clear()
    configure_public_adapter_registry(
        PublicAdapterRegistry(
            [
                FortunePublicAdapter(get_settings(), FakeChartClient()),
                DreamPublicAdapter.from_path(reference_path()),
            ]
        )
    )
    monkeypatch.setattr(router, "adapter_factory", RecordingAdapter)


def create_dream_session(client, payload=None):
    response = client.post(
        "/api/public/apps/dream/sessions",
        json=payload or dream_payload(),
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_dream_app_is_bootstrapped_disabled(client, workspace):
    app = next(item for item in json.loads((workspace / "apps.json").read_text()) if item["id"] == "dream")

    assert app == {
        "id": "dream",
        "name": "知梦",
        "slug": "dream",
        "agent_id": "dream-analysis-agent",
        "runtime_adapter": "dream",
        "enabled": False,
        "daily_limit": 3,
        "ttl_hours": 24,
        "max_questions": 20,
        "created_at": app["created_at"],
        "updated_at": app["updated_at"],
    }
    assert client.get("/api/public/apps/dream").status_code == 404


def test_dream_input_errors_do_not_create_session_or_reserve_quota(
    client, workspace, monkeypatch
):
    configure_dream_fakes(monkeypatch, workspace)
    requests = [
        {"json": dream_payload(dream_text="太短")},
        {"json": [dream_payload()]},
        {
            "content": b'{"dream_text":',
            "headers": {**ORIGIN, "content-type": "application/json"},
        },
    ]

    for request in requests:
        headers = request.pop("headers", ORIGIN)
        response = client.post("/api/public/apps/dream/sessions", headers=headers, **request)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_DREAM_INPUT"
        assert "Traceback" not in response.text

    assert PublicSessionRepository(workspace / "public_sessions").all() == []
    usage_files = list((workspace / "public_usage").glob("*.json"))
    assert not usage_files or all(json.loads(path.read_text()) == {} for path in usage_files)


def test_dream_full_flow_uses_empty_tools_and_keeps_public_context_private(
    client, workspace, monkeypatch
):
    configure_dream_fakes(monkeypatch, workspace)
    created = create_dream_session(client)
    session_id = created["session"]["id"]
    serialized = json.dumps(created, ensure_ascii=False)
    assert created["session"]["status"] == "context_ready"
    assert created["quota"]["remaining"] == 2
    assert dream_payload()["dream_text"] not in serialized
    assert dream_payload()["recent_context"] not in serialized
    assert "屋宅更新主大吉" not in serialized

    report = client.post(f"/api/public/apps/dream/sessions/{session_id}/report", headers=ORIGIN)
    assert report.status_code == 200, report.text
    assert '"type": "run.completed"' in report.text
    assert RecordingAdapter.calls[0]["tools"] == []
    system = RecordingAdapter.calls[0]["messages"][0]["content"]
    assert system.count("<USER_DREAM_DATA>") == 1
    assert system.count("<DREAM_REFERENCE_DATA>") == 1

    question = client.post(
        f"/api/public/apps/dream/sessions/{session_id}/messages",
        json={"content": "这个旧屋还可能和什么感受有关？"},
        headers=ORIGIN,
    )
    assert question.status_code == 200
    assert RecordingAdapter.calls[1]["tools"] == []
    restored = client.get(f"/api/public/apps/dream/sessions/{session_id}").json()
    assert restored["session"]["remaining_questions"] == 19
    assert [item["role"] for item in restored["messages"]] == ["assistant", "user", "assistant"]

    fortune_metadata = client.get("/api/public/apps/fortune").json()
    dream_metadata = client.get("/api/public/apps/dream").json()
    assert fortune_metadata["quota"]["remaining"] == 3
    assert dream_metadata["quota"]["remaining"] == 2
    assert PublicMetricsRepository(workspace / "public_metrics.json").read()["apps"]["dream"][
        "reports_completed"
    ] == 1

    assert client.delete(f"/api/public/apps/dream/sessions/{session_id}", headers=ORIGIN).status_code == 204
    assert client.get(f"/api/public/apps/dream/sessions/{session_id}").status_code == 404


def test_dream_no_match_and_cross_slug_access(client, workspace, monkeypatch):
    configure_dream_fakes(monkeypatch, workspace)
    created = create_dream_session(
        client,
        dream_payload(
            dream_text="电梯没有按钮，并且一直在陌生星球上横向移动。",
            emotions=["困惑"],
            recent_context=None,
        ),
    )
    session_id = created["session"]["id"]

    assert created["context"]["symbols"] == []
    report = client.post(f"/api/public/apps/dream/sessions/{session_id}/report", headers=ORIGIN)
    assert report.status_code == 200, report.text
    assert client.get(f"/api/public/apps/fortune/sessions/{session_id}").status_code == 404


def test_broken_dream_index_does_not_block_startup_or_fortune(workspace, monkeypatch, tmp_path):
    from app import main
    from app.config import get_settings

    broken = tmp_path / "broken-dream-symbols.json"
    broken.write_text("{", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_DIR", str(workspace))
    monkeypatch.setattr(main, "DREAM_REFERENCE_PATH", broken, raising=False)
    get_settings.cache_clear()
    with TestClient(main.create_app()) as client:
        enable_dream_app(workspace)
        dream_app = client.get("/api/apps/dream").json()
        assert dream_app["health"] == "reference_unavailable"
        unavailable = client.get("/api/public/apps/dream")
        assert unavailable.status_code == 503
        assert unavailable.json()["error"]["code"] == "DREAM_REFERENCE_UNAVAILABLE"
        assert client.get("/api/public/apps/fortune").status_code == 200
    get_settings.cache_clear()
