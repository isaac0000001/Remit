import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import (
    check_database_connection,
    close_database,
)

from app.api.auth import router as auth_router
from app.api.compliance import router as compliance_router
from app.api.ledger import router as ledger_router
from app.api.payments import router as payments_router


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

settings = get_settings()

APP_NAME = settings.APP_NAME
APP_VERSION = settings.API_VERSION
API_PREFIX = settings.API_PREFIX.rstrip("/")

APP_ENV = os.getenv(
    "APP_ENV",
    getattr(settings, "APP_ENV", "production"),
).lower()

IS_PRODUCTION = APP_ENV == "production"

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    ),
)

logger = logging.getLogger("remit")


# --------------------------------------------------
# LIFESPAN MANAGEMENT
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting %s API", APP_NAME)

    app.state.started_at = time.time()

    try:
        database_available = await check_database_connection()

        if not database_available:
            raise RuntimeError(
                "Database connection check failed."
            )

        logger.info("Database connection established.")

    except Exception:
        logger.exception(
            "Application startup database check failed."
        )

        await close_database()
        raise

    yield

    logger.info("Shutting down %s API", APP_NAME)

    try:
        await close_database()
        logger.info("Database connections closed.")

    except Exception:
        logger.exception(
            "Error while closing database connections."
        )


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    description=(
        "Remit - Secure international money transfer "
        "and remittance platform."
    ),
    version=APP_VERSION,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
    lifespan=lifespan,
)


# --------------------------------------------------
# REQUEST ID MIDDLEWARE
# --------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get(
            "X-Request-ID"
        ) or str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response


app.add_middleware(RequestIDMiddleware)


# --------------------------------------------------
# SECURITY HEADERS MIDDLEWARE
# --------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"

        response.headers["X-Frame-Options"] = "DENY"

        response.headers["Referrer-Policy"] = (
            "strict-origin-when-cross-origin"
        )

        response.headers["Cache-Control"] = (
            "no-store"
        )

        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        if IS_PRODUCTION:
            response.headers[
                "Strict-Transport-Security"
            ] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


app.add_middleware(SecurityHeadersMiddleware)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

cors_origins = getattr(
    settings,
    "CORS_ORIGINS",
    [],
)

if isinstance(cors_origins, str):
    cors_origins = [
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ]

if IS_PRODUCTION and (
    not cors_origins or "*" in cors_origins
):
    raise RuntimeError(
        "Production requires explicit CORS origins. "
        "Wildcard CORS is not permitted."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Request-ID",
        "Idempotency-Key",
    ],
    expose_headers=[
        "X-Request-ID",
    ],
    max_age=600,
)


# --------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# --------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:

    request_id = getattr(
        request.state,
        "request_id",
        None,
    )

    logger.exception(
        "Unhandled application exception. Request ID: %s",
        request_id,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": (
                    "An unexpected error occurred. "
                    "Please try again later."
                ),
            },
            "request_id": request_id,
        },
    )


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------

@app.get(
    "/",
    tags=["System"],
)
async def root():

    return {
        "success": True,
        "application": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "message": "Remit API is operational.",
    }


# --------------------------------------------------
# BASIC HEALTH CHECK
# --------------------------------------------------

@app.get(
    "/health",
    tags=["System"],
)
async def health_check():

    return {
        "success": True,
        "status": "healthy",
        "application": APP_NAME,
    }


# --------------------------------------------------
# DATABASE READINESS CHECK
# --------------------------------------------------

@app.get(
    "/health/ready",
    tags=["System"],
)
async def readiness_check():

    try:

        database_ok = await check_database_connection()

        if not database_ok:

            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "status": "not_ready",
                    "database": "unavailable",
                },
            )

        return {
            "success": True,
            "status": "ready",
            "database": "connected",
        }

    except Exception:

        logger.exception(
            "Database readiness check failed."
        )

        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "not_ready",
                "database": "unavailable",
            },
        )


# --------------------------------------------------
# SYSTEM STATUS
# --------------------------------------------------

@app.get(
    f"{API_PREFIX}/system/status",
    tags=["System"],
)
async def system_status():

    uptime = time.time() - getattr(
        app.state,
        "started_at",
        time.time(),
    )

    return {
        "success": True,
        "application": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
        "status": "operational",
        "uptime_seconds": round(uptime, 2),
    }


# --------------------------------------------------
# API ROUTERS
# --------------------------------------------------

app.include_router(auth_router)

app.include_router(compliance_router)

app.include_router(ledger_router)

app.include_router(payments_router)


# --------------------------------------------------
# END OF APPLICATION
# --------------------------------------------------
