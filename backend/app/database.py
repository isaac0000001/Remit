from collections.abc import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


engine = None
AsyncSessionLocal = None


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

if settings.DATABASE_URL:

    # Read database URL from secure settings
    raw_database_url = settings.DATABASE_URL.get_secret_value()

    # Parse URL and force the asyncpg driver
    parsed_url = make_url(raw_database_url)

    if parsed_url.get_backend_name() != "postgresql":
        raise ValueError(
            "DATABASE_URL must point to a PostgreSQL database."
        )

    database_url = parsed_url.set(
        drivername="postgresql+asyncpg"
    )

    # Create asynchronous database engine
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )

    # Create asynchronous session factory
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# ==========================================
# DATABASE SESSION
# ==========================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:

    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not configured",
        )

    async with AsyncSessionLocal() as session:

        try:
            yield session

        except Exception:
            await session.rollback()
            raise


# ==========================================
# CLOSE DATABASE CONNECTION
# ==========================================

async def close_database():

    if engine is not None:
        await engine.dispose()


# ==========================================
# CHECK DATABASE CONNECTION
# ==========================================

async def check_database_connection() -> bool:

    if engine is None:
        return False

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        return True

    except Exception:
        return False
