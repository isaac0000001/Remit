from fastapi import APIRouter, Depends

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


@router.post(
    "/",
    response_model=WalletResponse,
    status_code=201,
)
async def create_wallet(
    data: WalletCreate,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
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
    wallet_id: str,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):

    from uuid import UUID

    balance = await LedgerService.get_wallet_balance(
        db=db,
        customer_id=customer.id,
        wallet_id=UUID(wallet_id),
    )

    return balance
