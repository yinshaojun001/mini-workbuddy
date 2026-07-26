import json
from pathlib import Path


def test_bootstrap_creates_local_workspace(client, workspace: Path):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    for filename in ("models.json", "tools.json", "agents.json"):
        assert (workspace / filename).is_file()
    for dirname in ("skills", "agents", "sessions", "runs", "runtime"):
        assert (workspace / dirname).is_dir()

    tools = json.loads((workspace / "tools.json").read_text())
    models = json.loads((workspace / "models.json").read_text())
    deepseek = next(model for model in models if model["id"] == "deepseek-default")
    assert deepseek["model"] == "deepseek-v4-flash"
    assert [tool["id"] for tool in tools] == [
        "read_file",
        "write_file",
        "run_command",
    ]


def test_bootstrap_is_idempotent(client, workspace: Path):
    models_path = workspace / "models.json"
    original = models_path.read_text()

    assert client.get("/api/health").status_code == 200
    assert models_path.read_text() == original
