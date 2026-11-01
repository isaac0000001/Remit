from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):

    amount: Decimal = Field(
        gt=0,
        max_digits=20,
        decimal_places=8,
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
    )


class PaymentResponse(BaseModel):

    payment_id: UUID
    tx_ref: str
    amount: Decimal
    currency: str
    status: str
    checkout_url: str | None = None


class PaymentVerificationResponse(BaseModel):

    payment_id: UUID
    tx_ref: str
    status: str
    amount: Decimal
    currency: str
