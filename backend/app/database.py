from collections.abc import AsyncGenerator
import logging
from typing import Optional

from fastapi import HTTPException, status
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


logger = logging.getLogger(__name__)


# =========================================================
# DATABASE STATE
# =========================================================

engine: Optional[AsyncEngine] = None

AsyncSessionLocal: Optional[
    async_sessionmaker[AsyncSession]
] = None


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

def configure_database() -> None:
    """
    Configure the asynchronous PostgreSQL database.
    Supports both Pydantic SecretStr and ordinary strings.
    """

    global engine, AsyncSessionLocal

    database_setting = getattr(
        settings,
        "DATABASE_URL",
        None,
    )

    if not database_setting:
        logger.warning(
            "DATABASE_URL is missing. Database is unavailable."
        )
        return

    try:
        if isinstance(database_setting, SecretStr):
            raw_database_url = (
                database_setting.get_secret_value()
            )
        else:
            raw_database_url = str(database_setting).strip()

        if not raw_database_url:
            raise ValueError("DATABASE_URL cannot be empty.")

        parsed_url = make_url(raw_database_url)

        if parsed_url.get_backend_name() != "postgresql":
            raise ValueError(
                "DATABASE_URL must use PostgreSQL."
            )

        # Always use the asynchronous PostgreSQL driver.
        async_database_url = parsed_url.set(
            drivername="postgresql+asyncpg"
        )

        engine = create_async_engine(
            async_database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={
                "server_settings": {
                    "application_name": "Remit",
                }
            },
        )

        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        logger.info(
            "Asynchronous PostgreSQL database configured."
        )

    except Exception:
        engine = None
        AsyncSessionLocal = None

        logger.exception(
            "Failed to configure the database."
        )
        raise


# Configure once when this module is imported.
configure_database()


# =========================================================
# DATABASE SESSION DEPENDENCY
# =========================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an asynchronous database session to FastAPI routes.
    Rolls back an unfinished transaction when an error occurs.
    """

    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is unavailable.",
        )

    async with AsyncSessionLocal() as session:
        try:
            yield session

        except Exception:
            await session.rollback()
            logger.exception(
                "Database session failed. Transaction rolled back."
            )
            raise


# =========================================================
# DATABASE CONNECTION CHECK
# =========================================================

async def check_database_connection() -> bool:
    """
    Checks whether PostgreSQL is reachable.
    """

    if engine is None:
        logger.error(
            "Database health check failed: engine is not configured."
        )
        return False

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        return True

    except Exception:
        logger.exception(
            "PostgreSQL connection health check failed."
        )
        return False


# =========================================================
# DATABASE SHUTDOWN
# =========================================================

async def close_database() -> None:
    """
    Gracefully closes the database connection pool.
    """

    global engine

    if engine is not None:
        await engine.dispose()

        logger.info(
            "PostgreSQL connection pool closed."
        )


# =========================================================
# DATABASE AVAILABILITY
# =========================================================

def is_database_configured() -> bool:
    """
    Returns whether the database engine is configured.
    """

    return engine is not None
