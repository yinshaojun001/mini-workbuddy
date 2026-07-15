from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.agents.router import router as agents_router
from app.models.router import router as models_router
from app.runs.router import router as runs_router
from app.runtime.router import router as runtime_router
from app.sessions.router import router as sessions_router
from app.skills.router import router as skills_router
from app.storage.bootstrap import bootstrap_workspace
from app.tools.router import router as tools_router


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        bootstrap_workspace(settings.workspace_dir)
        yield

    app = FastAPI(title="Mini-workbuddy API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
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

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
