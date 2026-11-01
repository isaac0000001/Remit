from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Remit"
    APP_ENV: str = "development"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: SecretStr | None = None
    REDIS_URL: SecretStr | None = None

    SECRET_KEY: SecretStr = Field(min_length=32)

    CORS_ORIGINS: str = "http://localhost:3000"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Flutterwave configuration
    FLW_SECRET_KEY: SecretStr | None = None
    FLW_SECRET_HASH: SecretStr | None = None

    FLW_BASE_URL: str = "https://api.flutterwave.com/v3"

    FLW_REDIRECT_URL: str | None = None

    # Payments remain disabled in live mode until explicitly authorised.
    FLW_LIVE_PAYMENTS_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("APP_ENV")
    @classmethod
    def validate_environment(cls, value):
        allowed = {
            "development",
            "testing",
            "staging",
            "production",
        }

        if value not in allowed:
            raise ValueError("Invalid application environment")

        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret(cls, value):
        secret = value.get_secret_value()

        if len(secret) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")

        if secret in {
            "CHANGE_THIS_BEFORE_DEPLOYMENT",
            "your-secret-key",
            "secret",
        }:
            raise ValueError("A secure SECRET_KEY is required")

        return value

    @property
    def cors_origins_list(self):
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
