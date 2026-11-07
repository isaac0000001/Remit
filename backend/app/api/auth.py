import logging
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
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


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False)


# =========================================================
# DEPENDENCIES
# =========================================================

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db),
]

BearerCredentials = Annotated[
    Optional[HTTPAuthorizationCredentials],
    Depends(bearer_scheme),
]


# =========================================================
# ACCOUNT STATUS
# =========================================================

def ensure_account_is_active(customer: Customer) -> None:
    """
    Prevent suspended and closed accounts from accessing
    protected authentication endpoints.
    """

    if customer.status in (
        CustomerStatus.SUSPENDED,
        CustomerStatus.CLOSED,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is unavailable.",
        )


# =========================================================
# CUSTOMER REGISTRATION
# =========================================================

@router.post(
    "/register",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_customer(
    data: CustomerRegister,
    db: DatabaseSession,
):
    email = str(data.email).strip().lower()

    existing = await db.execute(
        select(Customer).where(
            Customer.email == email
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to register with these details.",
        )

    customer = Customer(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        phone_number=data.phone_number,
        country=data.country.strip().upper(),
        status=CustomerStatus.PENDING,
        email_verified=False,
    )

    db.add(customer)

    try:
        await db.commit()
        await db.refresh(customer)

    except IntegrityError as exc:
        await db.rollback()

        logger.warning(
            "Customer registration rejected because of a database constraint."
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to register with these details.",
        ) from exc

    except Exception:
        await db.rollback()
        logger.exception("Customer registration failed.")
        raise

    return customer


# =========================================================
# CUSTOMER LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login_customer(
    data: CustomerLogin,
    db: DatabaseSession,
):
    email = str(data.email).strip().lower()

    result = await db.execute(
        select(Customer).where(
            Customer.email == email
        )
    )

    customer = result.scalar_one_or_none()

    # Use the same response for incorrect email/password.
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not verify_password(
        data.password,
        customer.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    ensure_account_is_active(customer)

    token = create_access_token(
        str(customer.id)
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=(
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        ),
    )


# =========================================================
# CURRENT CUSTOMER AUTHENTICATION
# =========================================================

async def get_current_customer(
    credentials: BearerCredentials,
    db: DatabaseSession,
) -> Customer:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    try:
        payload = decode_access_token(
            credentials.credentials
        )

        customer_id = payload.get("sub")

        if not isinstance(customer_id, str) or not customer_id:
            raise InvalidTokenError(
                "Invalid token subject."
            )

    except (
        InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        ) from exc

    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id
        )
    )

    customer = result.scalar_one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    ensure_account_is_active(customer)

    return customer


# =========================================================
# CUSTOMER PROFILE
# =========================================================

@router.get(
    "/me",
    response_model=CustomerResponse,
)
async def get_my_profile(
    customer: Annotated[
        Customer,
        Depends(get_current_customer),
    ],
):
    return customer


# =========================================================
# END
# =========================================================
