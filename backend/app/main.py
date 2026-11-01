from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.config import settings
from app.database import close_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(
    title=settings.APP_NAME,
    description="Global Remittance Platform API",
    version=settings.API_VERSION,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.include_router(
    auth_router,
    prefix=settings.API_PREFIX,
)


@app.get("/")
async def root():
    return {
        "application": "Remit",
        "status": "running",
        "version": settings.API_VERSION,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "remit-api",
    }


@app.get(f"{settings.API_PREFIX}/system/status")
async def system_status():
    return {
        "application": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "status": "operational",
    }
