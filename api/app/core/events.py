from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy import text

from app.core import cache
from app.db.base import Base
from app.db.session import engine
from app.memory import graph_store

# Import all models so Base.metadata knows about every table
import app.db.models  # noqa: F401

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        logger.info("startup: enabling pgvector extension")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("startup: creating tables")
        await conn.run_sync(Base.metadata.create_all)

    logger.info("startup: platform ready")
    yield

    logger.info("shutdown: closing connections")
    await engine.dispose()
    await cache.close()
    await graph_store.close()
