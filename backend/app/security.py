from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
)
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.config import settings


# =========================================================
# SECURITY CONFIGURATION
# =========================================================

password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"
TOKEN_ISSUER = "remit-api"


# =========================================================
# PASSWORD VALIDATION
# =========================================================

def validate_password(password: str) -> None:
    """
    Validate password input before hashing.
    """

    if not isinstance(password, str):
        raise ValueError("Password must be a string.")

    if len(password) < 12:
        raise ValueError(
            "Password must contain at least 12 characters."
        )

    if len(password) > 128:
        raise ValueError(
            "Password must not exceed 128 characters."
        )


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password: str) -> str:
    """
    Hash passwords using the recommended Argon2 configuration.
    """

    validate_password(password)

    return password_hash.hash(password)


# =========================================================
# PASSWORD VERIFICATION
# =========================================================

def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a password against its stored Argon2 hash.
    """

    if not isinstance(password, str):
        return False

    if not isinstance(hashed_password, str):
        return False

    if not password or len(password) > 128:
        return False

    if not hashed_password:
        return False

    try:
        return password_hash.verify(
            password,
            hashed_password,
        )

    except (
        InvalidHashError,
        VerificationError,
        ValueError,
    ):
        return False


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Generate a signed JWT access token.
    """

    if not isinstance(subject, str) or not subject.strip():
        raise ValueError(
            "A valid token subject is required."
        )

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    if expires_delta.total_seconds() <= 0:
        raise ValueError(
            "Token expiration must be in the future."
        )

    now = datetime.now(timezone.utc)

    expires = now + expires_delta

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires,
        "iss": TOKEN_ISSUER,
        "type": "access",
    }

    secret = settings.SECRET_KEY.get_secret_value()

    return jwt.encode(
        payload,
        secret,
        algorithm=ALGORITHM,
    )


# =========================================================
# DECODE AND VERIFY ACCESS TOKEN
# =========================================================

def decode_access_token(token: str) -> dict[str, Any]:
    """
    Verify JWT signature, issuer, expiration and required claims.
    """

    if not isinstance(token, str) or not token:
        raise InvalidTokenError(
            "Access token is missing."
        )

    if len(token) > 8192:
        raise InvalidTokenError(
            "Access token is too large."
        )

    secret = settings.SECRET_KEY.get_secret_value()

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            options={
                "require": [
                    "exp",
                    "iat",
                    "sub",
                    "iss",
                    "type",
                ],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
            },
        )

    except InvalidTokenError:
        raise

    except (TypeError, ValueError) as exc:
        raise InvalidTokenError(
            "Invalid access token."
        ) from exc

    # Ensure the token is an access token.
    if payload.get("type") != "access":
        raise InvalidTokenError(
            "Invalid token type."
        )

    # Validate customer identifier.
    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise InvalidTokenError(
            "Invalid token subject."
        )

    return payload


# =========================================================
# END
# =========================================================
