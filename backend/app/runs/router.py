from fastapi import APIRouter

from app.config import get_settings
from app.runs.repository import RunRepository

router = APIRouter(prefix="/api/runs", tags=["运行记录"])


def repo() -> RunRepository:
    return RunRepository(get_settings().workspace_dir / "runs")


@router.get("")
def list_runs() -> list[dict]:
    return repo().list()


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    return {"id": run_id, "events": repo().events(run_id)}

