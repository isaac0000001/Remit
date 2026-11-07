from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WalletCreate(BaseModel):
    currency: str = Field(
        min_length=3,
        max_length=3,
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        value = value.strip().upper()

        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code")

        return value


class WalletResponse(BaseModel):
    wallet_id: UUID
    currency: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class WalletBalanceResponse(BaseModel):
    wallet_id: UUID
    currency: str
    balance: Decimal = Field(ge=0)
    status: str

    model_config = ConfigDict(from_attributes=True)
