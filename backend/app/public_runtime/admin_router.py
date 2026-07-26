from typing import Literal

from fastapi import APIRouter, Query, Response

from app.apps.repository import AppRepository
from app.config import get_settings
from app.public_runtime.admin_service import PublicRunsAdminService
from app.public_runtime.events import PublicRunEventRepository
from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.repository import PublicSessionRepository

router = APIRouter(prefix="/api/public-runs", tags=["公开运行"])


def service() -> PublicRunsAdminService:
    root = get_settings().workspace_dir
    return PublicRunsAdminService(
        PublicSessionRepository(root / "public_sessions"),
        PublicRunEventRepository(root / "public_sessions"),
        PublicMetricsRepository(root / "public_metrics.json"),
        QuotaRepository(root / "public_usage"),
        AppRepository(root / "apps.json"),
    )


@router.get("")
def list_public_runs(
    app_id: str | None = None,
    status: Literal["active", "running", "completed", "failed", "expired"] | None = None,
    query: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=1000),
) -> dict:
    return service().list_sessions(
        app_id=app_id,
        status=status,
        query=query,
        limit=limit,
        cursor=cursor,
    )


@router.get("/stats")
def public_run_stats() -> dict:
    return service().stats()


@router.get("/{session_id}")
def public_run_detail(session_id: str, include_sensitive: bool = False) -> dict:
    return service().detail(session_id, include_sensitive)


@router.delete("/{session_id}", status_code=204)
def delete_public_run(session_id: str) -> Response:
    service().delete(session_id)
    return Response(status_code=204)
