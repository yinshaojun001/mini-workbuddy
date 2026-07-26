from app.public_runtime.identity import hmac_hash, parse_token, visitor_identity


def test_signed_visitor_cookie_rejects_tampering():
    secret = "test-secret"
    assert parse_token(None, secret) is None
    assert parse_token("visitor.bad-signature", secret) is None
    assert hmac_hash("same", "visitor-key") != hmac_hash("same", "ip-key")


def test_public_metadata_sets_hardened_anonymous_cookie(client):
    response = client.get("/api/public/apps/fortune")
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "fortune_visitor=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/api/public/apps/fortune" in cookie
