from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.compliance import router as compliance_router
from app.api.ledger import router as ledger_router
from app.api.payments import router as payments_router

from app.config import settings
from app.database import (
    close_database,
    check_database_connection,
)


# ==========================================
# APPLICATION LIFECYCLE
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await close_database()


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Global Remittance Platform API",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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
        "X-Request-ID",
    ],
)


# ==========================================
# API ROUTERS
# ==========================================

app.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    compliance_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    payments_router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    ledger_router,
    prefix=settings.API_PREFIX,
)


# ==========================================
# ROOT ENDPOINT
# ==========================================

@app.get("/")
async def root():
    return {
        "application": "Remit",
        "status": "running",
        "version": settings.API_VERSION,
    }


# ==========================================
# APPLICATION HEALTH CHECK
# ==========================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "remit-api",
    }


# ==========================================
# DATABASE CONNECTION CHECK
# ==========================================

@app.get("/health/database")
async def database_health():

    connected = await check_database_connection()

    if not connected:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )

    return {
        "status": "healthy",
        "database": "connected",
    }


# ==========================================
# SYSTEM STATUS
# ==========================================

@app.get(f"{settings.API_PREFIX}/system/status")
async def system_status():
    return {
        "application": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "status": "operational",
    }
