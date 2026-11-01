from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerRegister(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    phone_number: str | None = Field(default=None, max_length=30)
    country: str = Field(min_length=2, max_length=2)


class CustomerLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class CustomerResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    country: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
