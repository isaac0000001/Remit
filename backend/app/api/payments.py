import uuid
import hmac

from decimal import Decimal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_customer
from app.config import settings
from app.database import get_db
from app.models import Customer
from app.payment_models import Payment, PaymentStatus
from app.payment_schemas import (
    PaymentCreate,
    PaymentResponse,
)
from app.services.flutterwave import (
    FlutterwaveError,
    FlutterwaveService,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


@router.post(
    "/checkout",
    response_model=PaymentResponse,
)
async def create_checkout(
    data: PaymentCreate,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):

    if settings.APP_ENV == "production":
        if not settings.FLW_LIVE_PAYMENTS_ENABLED:
            raise HTTPException(
                status_code=503,
                detail="Live payment collection is not enabled",
            )

    if customer.status.value != "active":
        raise HTTPException(
            status_code=403,
            detail="Customer account is not active",
        )

    if not settings.FLW_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Payment provider is not configured",
        )

    currency = data.currency.upper()

    tx_ref = f"REMIT-{uuid.uuid4().hex.upper()}"

    payment = Payment(
        customer_id=customer.id,
        tx_ref=tx_ref,
        amount=data.amount,
        currency=currency,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    try:

        service = FlutterwaveService()

        checkout_url = await service.create_payment(
            tx_ref=tx_ref,
            amount=data.amount,
            currency=currency,
            email=customer.email,
            name=(
                f"{customer.first_name} "
                f"{customer.last_name}"
            ),
            phone_number=customer.phone_number,
        )

        payment.checkout_url = checkout_url

        await db.commit()
        await db.refresh(payment)

    except Exception:

        await db.rollback()

        payment.status = PaymentStatus.FAILED
        payment.checkout_url = None

        await db.commit()

        raise HTTPException(
            status_code=502,
            detail="Unable to initialize payment",
        )

    return PaymentResponse(
        payment_id=payment.id,
        tx_ref=payment.tx_ref,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status.value,
        checkout_url=payment.checkout_url,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.customer_id == customer.id,
        )
    )

    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return PaymentResponse(
        payment_id=payment.id,
        tx_ref=payment.tx_ref,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status.value,
        checkout_url=payment.checkout_url,
    )


async def verify_and_update_payment(
    transaction_id: str,
    tx_ref: str,
    db: AsyncSession,
):

    result = await db.execute(
        select(Payment)
        .where(Payment.tx_ref == tx_ref)
        .with_for_update()
    )

    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment reference not found",
        )

    if payment.status == PaymentStatus.SUCCESSFUL:
        return payment

    if not transaction_id.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Invalid transaction identifier",
        )

    try:

        service = FlutterwaveService()

        verified = await service.verify_payment(
            transaction_id
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to verify payment with provider",
        )

    verified_amount = Decimal(str(verified.get("amount", "0")))
    verified_currency = str(
        verified.get("currency", "")
    ).upper()

    valid = (
        verified.get("status") == "successful"
        and verified.get("tx_ref") == payment.tx_ref
        and verified_currency == payment.currency
        and verified_amount >= payment.amount
    )

    if not valid:
        raise HTTPException(
            status_code=400,
            detail="Payment verification did not match expected details",
        )

    payment.status = PaymentStatus.SUCCESSFUL
    payment.provider_transaction_id = str(
        verified.get("id")
    )

    await db.commit()
    await db.refresh(payment)

    return payment


@router.post("/webhook")
async def flutterwave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):

    if not settings.FLW_SECRET_HASH:
        raise HTTPException(
            status_code=503,
            detail="Webhook authentication is not configured",
        )

    received_hash = request.headers.get("verif-hash")

    expected_hash = (
        settings.FLW_SECRET_HASH.get_secret_value()
    )

    if not received_hash or not hmac.compare_digest(
        received_hash,
        expected_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    payload = await request.json()

    event_data = payload.get("data", {})

    transaction_id = event_data.get("id")
    tx_ref = event_data.get("tx_ref")

    if not transaction_id or not tx_ref:
        return {"received": True}

    result = await db.execute(
        select(Payment).where(Payment.tx_ref == tx_ref)
    )

    payment = result.scalar_one_or_none()

    if not payment:
        return {"received": True}

    if payment.status == PaymentStatus.SUCCESSFUL:
        return {"received": True}

    await verify_and_update_payment(
        str(transaction_id),
        tx_ref,
        db,
    )

    return {"received": True}
