"""JWT token creation and validation service."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings
from app.models.token import BEARER_SCHEME, TokenPayload, TokenResponse, TokenType


def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "token_type": TokenType.ACCESS.value,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, role: str) -> str:
    """Create a JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "token_type": TokenType.REFRESH.value,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_token_pair(user_id: str, role: str) -> TokenResponse:
    """Create both access and refresh tokens."""
    access_token = create_access_token(user_id, role)
    refresh_token = create_refresh_token(user_id, role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=BEARER_SCHEME,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(token: str) -> TokenPayload | None:
    """Decode and validate a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**payload)
    except JWTError:
        return None


def create_password_reset_token(user_id: str) -> str:
    """Create a short-lived token for password reset."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=1)

    payload = {
        "sub": user_id,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "token_type": TokenType.PASSWORD_RESET.value,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
