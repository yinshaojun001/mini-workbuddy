import base64
import hashlib
import hmac
import secrets

from fastapi import Request, Response

COOKIE_NAME = "fortune_visitor"
COOKIE_PATH = "/api/public/apps/fortune"


def _signature(visitor_id: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), visitor_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def parse_token(token: str | None, secret: str) -> str | None:
    if not token or "." not in token:
        return None
    visitor_id, signature = token.split(".", 1)
    if len(visitor_id) != 43 or not hmac.compare_digest(signature, _signature(visitor_id, secret)):
        return None
    return visitor_id


def visitor_identity(request: Request, response: Response, secret: str) -> str:
    visitor_id = parse_token(request.cookies.get(COOKIE_NAME), secret)
    if visitor_id is None:
        visitor_id = secrets.token_urlsafe(32)
        response.set_cookie(
            COOKIE_NAME,
            f"{visitor_id}.{_signature(visitor_id, secret)}",
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            secure=not request.url.hostname in {"localhost", "127.0.0.1", "testserver"},
            samesite="lax",
            path=COOKIE_PATH,
        )
    return visitor_id


def hmac_hash(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
