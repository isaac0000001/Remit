from datetime import datetime, timedelta, timezone

import jwt
from argon2.exceptions import InvalidHashError, VerificationError
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.config import settings


password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    if not isinstance(password, str):
        raise ValueError("Password must be a string")

    if len(password) < 12:
        raise ValueError(
            "Password must contain at least 12 characters"
        )

    if len(password) > 128:
        raise ValueError("Password is too long")

    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    if not password or not hashed_password:
        return False

    try:
        return password_hash.verify(password, hashed_password)
    except (InvalidHashError, VerificationError):
        return False


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    if not subject:
        raise ValueError("Token subject is required")

    now = datetime.now(timezone.utc)

    expires = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires,
        "iss": "remit-api",
        "type": "access",
    }

    secret = settings.SECRET_KEY.get_secret_value()

    return jwt.encode(
        payload,
        secret,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    secret = settings.SECRET_KEY.get_secret_value()

    payload = jwt.decode(
        token,
        secret,
        algorithms=[ALGORITHM],
        issuer="remit-api",
        options={
            "require": [
                "exp",
                "iat",
                "sub",
                "iss",
                "type",
            ]
        },
    )

    if payload.get("type") != "access":
        raise InvalidTokenError("Invalid token type")

    subject = payload.get("sub")

    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError("Invalid token subject")

    return payload
