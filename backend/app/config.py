from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    workspace_dir: Path = Path(__file__).resolve().parents[2] / "workspace"
    frontend_origin: str = "http://localhost:5173"
    max_skill_zip_bytes: int = 10 * 1024 * 1024
    max_skill_expanded_bytes: int = 50 * 1024 * 1024
    max_tool_rounds: int = 8
    command_timeout_seconds: int = 30
    public_session_secret: str = "development-session-secret-change-in-production"
    public_ip_hash_secret: str = "development-ip-secret-change-in-production"
    bazi_engine_url: str = "http://fortune-bazi-engine:8080"
    fortune_origin: str = "http://localhost:5174"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
