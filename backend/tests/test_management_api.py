import io
import zipfile


def make_skill_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("writer/SKILL.md", "# 写作助手\n\n帮助整理中文内容。\n")
        archive.writestr("writer/references/style.md", "保持简洁。\n")
    return buffer.getvalue()


def test_model_crud_masks_secret_and_preserves_it(client):
    created = client.post(
        "/api/models",
        json={
            "name": "业务 Qwen",
            "provider": "qwen",
            "model": "qwen-plus",
            "base_url": "https://example.test/v1",
            "api_key": "secret-key-1234",
            "enabled": True,
            "temperature": 0.3,
            "max_tokens": 2048,
        },
    )
    assert created.status_code == 201
    model = created.json()
    assert "api_key" not in model
    assert model["has_api_key"] is True
    assert model["api_key_hint"] == "••••1234"

    updated = client.put(
        f"/api/models/{model['id']}",
        json={**model, "api_key": "", "name": "业务 Qwen 2"},
    )
    assert updated.status_code == 200
    assert updated.json()["has_api_key"] is True


def test_tools_are_fixed_and_only_enabled_can_change(client):
    tools = client.get("/api/tools").json()
    assert len(tools) == 3
    assert client.post("/api/tools", json={"name": "网络"}).status_code == 405
    assert client.delete("/api/tools/read_file").status_code == 405

    response = client.patch("/api/tools/read_file", json={"enabled": False})
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_skill_create_import_tree_and_toggle(client):
    invalid = client.post(
        "/api/skills",
        json={"name": "空技能", "description": "", "content": ""},
    )
    assert invalid.status_code == 422

    imported = client.post(
        "/api/skills/import",
        files={"file": ("writer.zip", make_skill_zip(), "application/zip")},
    )
    assert imported.status_code == 201
    skill = imported.json()
    detail = client.get(f"/api/skills/{skill['id']}").json()
    assert detail["content"].startswith("# 写作助手")
    assert detail["tree"][0]["name"] == "references"

    toggled = client.patch(f"/api/skills/{skill['id']}", json={"enabled": False})
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False


def test_agents_validate_bindings_prompt_and_builtin_delete(client):
    assert client.delete("/api/agents/main-agent").status_code == 409
    prompt = client.put(
        "/api/agents/main-agent/prompt",
        json={"content": "# 新提示词\n\n只使用中文。"},
    )
    assert prompt.status_code == 200
    assert client.get("/api/agents/main-agent/prompt").json()["content"].startswith("# 新")

    invalid = client.post(
        "/api/agents",
        json={
            "name": "无效 Agent",
            "description": "",
            "model_id": "missing",
            "tool_ids": [],
            "skill_ids": [],
            "work_directory": "",
            "enabled": True,
        },
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/agents",
        json={
            "name": "研发助手",
            "description": "处理本地研发任务",
            "model_id": "qwen-default",
            "tool_ids": ["read_file"],
            "skill_ids": [],
            "work_directory": "",
            "enabled": True,
        },
    )
    assert created.status_code == 201
    assert created.json()["work_directory"]
    assert created.json()["is_builtin"] is False

