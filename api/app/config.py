from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_HERE = Path(__file__).resolve().parent
_API_DIR = _HERE.parent
_ROOT_DIR = _API_DIR.parent
_ENV_FILES = [str(_API_DIR / ".env"), str(_ROOT_DIR / ".env")]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # ── Database (PostgreSQL + pgvector) ─────────────────────────────────────
    DATABASE_URL: str

    # ── Redis (session cache + OAuth state) ───────────────────────────────────
    REDIS_URL: str = ""   # empty = Redis disabled, falls back to in-memory
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # ── Neo4j (optional — graph memory) ──────────────────────────────────────
    NEO4J_URI: str = ""       # empty = Neo4j disabled, app still works
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # ── OpenAI (chat + embeddings) ────────────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4096

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GOOGLE_SCOPES: str = (
        "openid "
        "https://www.googleapis.com/auth/userinfo.email "
        "https://www.googleapis.com/auth/userinfo.profile "
        "https://www.googleapis.com/auth/gmail.modify "
        "https://www.googleapis.com/auth/calendar"
    )

    # ── Encryption ────────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str

    # ── Email Sync ────────────────────────────────────────────────────────────
    EMAIL_SYNC_INTERVAL_MINUTES: int = 5
    EMAIL_SYNC_MAX_RESULTS: int = 50

    # ── Memory ────────────────────────────────────────────────────────────────
    MEMORY_EMBEDDING_DIM: int = 1536
    MEMORY_SIMILARITY_THRESHOLD: float = 0.75
    MEMORY_MAX_CONTEXT_ITEMS: int = 10
    MEMORY_CONSOLIDATION_HOUR: int = 2

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def google_scopes_list(self) -> list[str]:
        raw = self.GOOGLE_SCOPES.replace(",", " ")
        return [s.strip() for s in raw.split() if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
