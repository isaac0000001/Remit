from collections.abc import AsyncGenerator
import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from pydantic import SecretStr

from app.config import settings


logger = logging.getLogger(__name__)

engine = None
AsyncSessionLocal = None


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

database_setting = getattr(settings, "DATABASE_URL", None)

if database_setting:

    try:
        # Support SecretStr and ordinary strings
        if isinstance(database_setting, SecretStr):
            raw_database_url = database_setting.get_secret_value()
        else:
            raw_database_url = str(database_setting)

        # Parse database URL
        parsed_url = make_url(raw_database_url)

        # Validate PostgreSQL
        if parsed_url.get_backend_name() != "postgresql":
            raise ValueError(
                "DATABASE_URL must point to PostgreSQL."
            )

        # Force asynchronous PostgreSQL driver
        database_url = parsed_url.set(
            drivername="postgresql+asyncpg"
        )

        # Create asynchronous engine
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                "server_settings": {
                    "application_name": "Remit"
                }
            },
        )

        # Create session factory
        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        logger.info("Database engine configured successfully.")

    except Exception:
        logger.exception("Database configuration failed.")
        raise

else:
    logger.warning(
        "DATABASE_URL is not configured. Database operations are disabled."
    )


# ==========================================
# DATABASE SESSION
# ==========================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:

    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=503,
            detail="Database service is not configured.",
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

async def close_database() -> None:

    global engine

    if engine is not None:
        await engine.dispose()
        logger.info("Database connections closed.")


# ==========================================
# CHECK DATABASE CONNECTION
# ==========================================

async def check_database_connection() -> bool:

    if engine is None:
        return False

    try:
        async with engine.connect() as connection:

            await connection.execute(
                text("SELECT 1")
            )

        return True

    except Exception:
        logger.exception("Database health check failed.")
        return False
