import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
APP_NAME: str = "Remit"
APP_ENV: str = "development"
API_VERSION: str = "1.0.0"
API_PREFIX: str = "/api/v1"

DATABASE_URL: str | None = None
REDIS_URL: str | None = None

# No default secret: deployment must supply SECRET_KEY.
SECRET_KEY: str = Field(min_length=32)

CORS_ORIGINS: str = "http://localhost:3000"

ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
    default=30,
    ge=5,
    le=60,
)

model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=True,
    extra="ignore",
)

@field_validator("SECRET_KEY")
@classmethod
def validate_secret_key(cls, value: str) -> str:
    if len(value) < 32:
        raise ValueError("SECRET_KEY must contain at least 32 characters")

    if value == "CHANGE_THIS_BEFORE_DEPLOYMENT":
        raise ValueError("Default development secret is not permitted")

    return value

@field_validator("APP_ENV")
@classmethod
def validate_environment(cls, value: str) -> str:
    allowed = {"development", "testing", "staging", "production"}

    if value not in allowed:
        raise ValueError("Invalid application environment")

    return value

@lru_cache
def get_settings() -> Settings:
return Settings()

settings = get_settings()
