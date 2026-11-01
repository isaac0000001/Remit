from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WalletCreate(BaseModel):

    currency: str = Field(
        min_length=3,
        max_length=3,
    )


class WalletResponse(BaseModel):

    wallet_id: UUID
    currency: str
    status: str


class WalletBalanceResponse(BaseModel):

    wallet_id: str
    currency: str
    balance: Decimal
    status: str
