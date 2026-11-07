import re
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class CustomerRegister(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    phone_number: str | None = Field(default=None, max_length=30)
    country: str = Field(min_length=2, max_length=2)

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")

        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+", value):
            raise ValueError("Name contains invalid characters")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        value = value.strip().upper()

        if not re.fullmatch(r"[A-Z]{2}", value):
            raise ValueError("Country must be a two-letter country code")

        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        if not re.fullmatch(r"\+?[0-9 ()-]{7,30}", value):
            raise ValueError("Invalid phone number")

        return value


class CustomerLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class CustomerResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    country: str
    status: str

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)
