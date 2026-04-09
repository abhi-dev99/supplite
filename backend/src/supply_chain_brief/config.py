from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        parsed = int(raw_value)
    except ValueError as exc:  # pragma: no cover - defensive configuration guard
        raise ValueError(f"Environment variable {name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"Environment variable {name} must be greater than zero")
    return parsed


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_env: str
    database_path: Path
    model_version: str
    llm_provider: str
    anthropic_api_key: str | None
    openai_api_key: str | None
    cors_origins: tuple[str, ...]
    request_timeout_seconds: int
    cache_ttl_minutes: int
    max_brief_skus: int

    @property
    def use_remote_llm(self) -> bool:
        return self.llm_provider in {"anthropic", "openai", "auto"}


def load_config() -> AppConfig:
    database_path = Path(os.getenv("DATABASE_PATH", "./data/demand_intelligence.db"))
    default_cors = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:8501"
    return AppConfig(
        app_env=os.getenv("APP_ENV", "development").strip().lower(),
        database_path=database_path,
        model_version=os.getenv("MODEL_VERSION", "brief-v1").strip(),
        llm_provider=os.getenv("LLM_PROVIDER", "deterministic").strip().lower(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        cors_origins=tuple(_parse_csv(os.getenv("CORS_ORIGINS", default_cors))),
        request_timeout_seconds=_read_int("REQUEST_TIMEOUT_SECONDS", 20),
        cache_ttl_minutes=_read_int("CACHE_TTL_MINUTES", 1440),
        max_brief_skus=_read_int("MAX_BRIEF_SKUS", 5),
    )
