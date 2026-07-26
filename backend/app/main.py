import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import register_error_handlers
from app.apps.router import router as apps_router
from app.bootstrap.fortune import bootstrap_fortune
from app.agents.router import router as agents_router
from app.models.router import router as models_router
from app.runs.router import router as runs_router
from app.runtime.router import router as runtime_router
from app.public_runtime.cleanup import cleanup_expired_sessions, cleanup_loop, stop_cleanup_task
from app.public_runtime.admin_router import router as public_runs_admin_router
from app.public_runtime.metrics import PublicMetricsRepository
from app.public_runtime.repository import PublicSessionRepository
from app.public_runtime.quota import QuotaRepository
from app.public_runtime.router import router as public_runtime_router
from app.public_runtime.rate_limit import public_rate_limiter
from app.sessions.router import router as sessions_router
from app.skills.router import router as skills_router
from app.storage.bootstrap import bootstrap_workspace
from app.tools.router import router as tools_router


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        bootstrap_workspace(settings.workspace_dir)
        bootstrap_fortune(settings.workspace_dir)
        public_rate_limiter.clear()
        sessions = PublicSessionRepository(settings.workspace_dir / "public_sessions")
        quota = QuotaRepository(settings.workspace_dir / "public_usage")
        metrics = PublicMetricsRepository(settings.workspace_dir / "public_metrics.json")
        cleanup_expired_sessions(sessions, quota, metrics)
        cleanup_task = asyncio.create_task(cleanup_loop(sessions, quota, metrics))
        try:
            yield
        finally:
            await stop_cleanup_task(cleanup_task)

    app = FastAPI(title="Mini-workbuddy API", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def limit_public_request_body(request: Request, call_next):
        if request.url.path.startswith("/api/public/apps/") and request.method in {"POST", "PUT", "PATCH"}:
            declared = request.headers.get("content-length")
            try:
                too_large = bool(declared) and int(declared) > 16 * 1024
            except ValueError:
                too_large = True
            if too_large:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": "请求内容不能超过 16 KB",
                            "details": {},
                        }
                    },
                )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, settings.fortune_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(models_router)
    app.include_router(tools_router)
    app.include_router(skills_router)
    app.include_router(agents_router)
    app.include_router(sessions_router)
    app.include_router(runs_router)
    app.include_router(runtime_router)
    app.include_router(apps_router)
    app.include_router(public_runs_admin_router)
    app.include_router(public_runtime_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
