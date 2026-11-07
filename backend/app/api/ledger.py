from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_customer
from app.database import get_db
from app.ledger_schemas import (
    WalletBalanceResponse,
    WalletCreate,
    WalletResponse,
)
from app.models import Customer
from app.services.ledger import LedgerService


router = APIRouter(
    prefix="/wallets",
    tags=["Wallets and Ledger"],
)


CurrentCustomer = Annotated[
    Customer,
    Depends(get_current_customer),
]

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db),
]


@router.post(
    "/",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wallet(
    data: WalletCreate,
    customer: CurrentCustomer,
    db: DatabaseSession,
):
    wallet = await LedgerService.create_customer_wallet(
        db=db,
        customer=customer,
        currency=data.currency,
    )

    return WalletResponse(
        wallet_id=wallet.id,
        currency=wallet.currency,
        status=wallet.status.value,
    )


@router.get(
    "/{wallet_id}/balance",
    response_model=WalletBalanceResponse,
)
async def get_wallet_balance(
    wallet_id: UUID,
    customer: CurrentCustomer,
    db: DatabaseSession,
):
    balance = await LedgerService.get_wallet_balance(
        db=db,
        customer_id=customer.id,
        wallet_id=wallet_id,
    )

    return balance
