import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text

from alembic import command
from app.core import cache
from app.db.session import engine
from app.memory import graph_store

logger = structlog.get_logger()

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _run_migrations() -> None:
    cfg = Config(str(_ALEMBIC_INI))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup: enabling pgvector extension")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    logger.info("startup: running database migrations")
    try:
        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _run_migrations),
            timeout=30.0,
        )
    except TimeoutError:
        logger.warning("startup: migration timed out after 30s — server will start anyway")
    except Exception as exc:
        logger.warning("startup: migration failed — server will start anyway", error=str(exc)[:200])

    logger.info("startup: platform ready")
    yield

    logger.info("shutdown: closing connections")
    await engine.dispose()
    await cache.close()
    await graph_store.close()
