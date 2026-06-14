from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=not settings.is_production,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,          # recycle connections every 5 min (Neon idle timeout)
    pool_timeout=30,
    connect_args={
        "timeout": 30,
        "command_timeout": 60,
        "statement_cache_size": 0,       # required for Neon/PgBouncer transaction mode
        "prepared_statement_cache_size": 0,
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
