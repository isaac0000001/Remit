from functools import lru_cache

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # =====================================================
    # APPLICATION
    # =====================================================

    APP_NAME: str = "Remit"
    APP_ENV: str = "development"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # =====================================================
    # DATABASE AND CACHE
    # =====================================================

    DATABASE_URL: SecretStr | None = None
    REDIS_URL: SecretStr | None = None

    # =====================================================
    # SECURITY
    # =====================================================

    SECRET_KEY: SecretStr = Field(min_length=32)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=5,
        le=1440,
    )

    CORS_ORIGINS: str = "http://localhost:3000"

    # =====================================================
    # FLUTTERWAVE
    # =====================================================

    FLW_SECRET_KEY: SecretStr | None = None
    FLW_SECRET_HASH: SecretStr | None = None

    FLW_BASE_URL: str = "https://api.flutterwave.com/v3"

    FLW_REDIRECT_URL: str | None = None

    FLW_LIVE_PAYMENTS_ENABLED: bool = False

    # =====================================================
    # PYDANTIC CONFIGURATION
    # =====================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )

    # =====================================================
    # ENVIRONMENT VALIDATION
    # =====================================================

    @field_validator("APP_ENV")
    @classmethod
    def validate_environment(cls, value: str) -> str:

        allowed = {
            "development",
            "testing",
            "staging",
            "production",
        }

        value = value.strip().lower()

        if value not in allowed:
            raise ValueError(
                "APP_ENV must be development, testing, staging, or production."
            )

        return value

    # =====================================================
    # API PREFIX VALIDATION
    # =====================================================

    @field_validator("API_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:

        value = value.strip()

        if not value.startswith("/"):
            raise ValueError(
                "API_PREFIX must start with '/'."
            )

        if value != "/" and value.endswith("/"):
            value = value.rstrip("/")

        return value

    # =====================================================
    # SECRET KEY VALIDATION
    # =====================================================

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:

        secret = value.get_secret_value()

        if len(secret) < 32:
            raise ValueError(
                "SECRET_KEY must contain at least 32 characters."
            )

        insecure_values = {
            "CHANGE_THIS_BEFORE_DEPLOYMENT",
            "your-secret-key",
            "secret",
        }

        if secret in insecure_values:
            raise ValueError(
                "A secure SECRET_KEY is required."
            )

        return value

    # =====================================================
    # CORS VALIDATION
    # =====================================================

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:

        origins = [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]

        if not origins:
            raise ValueError(
                "At least one CORS origin must be configured."
            )

        for origin in origins:

            if origin == "*":
                continue

            if not origin.startswith(("http://", "https://")):
                raise ValueError(
                    "CORS origins must start with http:// or https://."
                )

            if origin.endswith("/"):
                raise ValueError(
                    "CORS origins must not end with a slash."
                )

        return ",".join(origins)

    # =====================================================
    # PRODUCTION VALIDATION
    # =====================================================

    @model_validator(mode="after")
    def validate_production_configuration(self):

        if self.APP_ENV == "production":

            if self.DATABASE_URL is None:
                raise ValueError(
                    "DATABASE_URL is required in production."
                )

            origins = self.cors_origins_list

            if "*" in origins:
                raise ValueError(
                    "Wildcard CORS is not permitted in production."
                )

            if any(
                "localhost" in origin or "127.0.0.1" in origin
                for origin in origins
            ):
                raise ValueError(
                    "Localhost CORS origins are not permitted in production."
                )

            if self.FLW_LIVE_PAYMENTS_ENABLED:
                if not self.FLW_SECRET_KEY or not self.FLW_SECRET_HASH:
                    raise ValueError(
                        "Flutterwave credentials are required when live payments are enabled."
                    )

        return self

    # =====================================================
    # CORS HELPER
    # =====================================================

    @property
    def cors_origins_list(self) -> list[str]:

        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


# =========================================================
# SETTINGS FACTORY
# =========================================================

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
