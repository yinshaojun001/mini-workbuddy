def app_payload(**updates):
    payload = {
        "name": "测试发布应用",
        "slug": "test-app",
        "agent_id": "main-agent",
        "enabled": True,
        "daily_limit": 3,
        "ttl_hours": 24,
        "max_questions": 20,
    }
    payload.update(updates)
    return payload


def test_apps_crud_validates_slug_agent_and_limits(client):
    assert any(item["id"] == "fortune" for item in client.get("/api/apps").json())
    created = client.post("/api/apps", json=app_payload())
    assert created.status_code == 201
    app = created.json()
    assert app["health"] == "model_unavailable"
    assert app["public_url"].endswith("/")

    assert client.post("/api/apps", json=app_payload()).status_code == 409
    assert client.post("/api/apps", json=app_payload(slug="Bad Slug")).status_code == 422
    assert client.post("/api/apps", json=app_payload(agent_id="missing")).status_code == 404
    assert client.post("/api/apps", json=app_payload(daily_limit=0)).status_code == 422

    updated = client.put(f"/api/apps/{app['id']}", json=app_payload(name="新名称", slug="new-slug"))
    assert updated.status_code == 200
    assert updated.json()["name"] == "新名称"
    assert client.delete(f"/api/apps/{app['id']}").status_code == 204
    assert client.get(f"/api/apps/{app['id']}").status_code == 404
