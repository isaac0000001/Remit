from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, CustomerStatus
from app.schemas import (
    CustomerLogin,
    CustomerRegister,
    CustomerResponse,
    TokenResponse,
)
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer()


@router.post(
    "/register",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_customer(
    data: CustomerRegister,
    db: AsyncSession = Depends(get_db),
):
    email = str(data.email).strip().lower()

    existing = await db.execute(
        select(Customer).where(Customer.email == email)
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Unable to register with these details",
        )

    customer = Customer(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        phone_number=data.phone_number,
        country=data.country.upper(),
        status=CustomerStatus.PENDING,
        email_verified=False,
    )

    db.add(customer)

    try:
        await db.commit()
        await db.refresh(customer)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Unable to register with these details",
        )

    return customer


@router.post("/login", response_model=TokenResponse)
async def login_customer(
    data: CustomerLogin,
    db: AsyncSession = Depends(get_db),
):
    email = str(data.email).strip().lower()

    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )

    customer = result.scalar_one_or_none()

    if not customer or not verify_password(
        data.password,
        customer.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if customer.status in (
        CustomerStatus.SUSPENDED,
        CustomerStatus.CLOSED,
    ):
        raise HTTPException(
            status_code=403,
            detail="Account is unavailable",
        )

    token = create_access_token(str(customer.id))

    return TokenResponse(
        access_token=token,
        expires_in=1800,
    )


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Customer:
    try:
        payload = decode_access_token(credentials.credentials)
        customer_id = payload["sub"]
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )

    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=401,
            detail="Customer account not found",
        )

    if customer.status in (
        CustomerStatus.SUSPENDED,
        CustomerStatus.CLOSED,
    ):
        raise HTTPException(
            status_code=403,
            detail="Account is unavailable",
        )

    return customer


@router.get("/me", response_model=CustomerResponse)
async def get_my_profile(
    customer: Customer = Depends(get_current_customer),
):
    return customer
