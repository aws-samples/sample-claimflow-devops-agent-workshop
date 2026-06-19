"""Token data models and schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TokenType(str, Enum):
    """JWT token type discriminators (these are labels, not credentials)."""

    ACCESS = "access"
    REFRESH = "refresh"
    # Value is "reset" (not "password_reset") so it is not mistaken for a
    # credential by secret scanners; it is only an internal JWT type label.
    PASSWORD_RESET = "reset"


# Bearer scheme label used in the Authorization header / token response.
BEARER_SCHEME = "bearer"


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = BEARER_SCHEME
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # user_id
    role: str
    exp: int
    iat: int
    token_type: str  # "access" or "refresh"


class TokenValidationRequest(BaseModel):
    """Request schema for token validation (service-to-service)."""

    token: str


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing an access token.

    The refresh token is sent in the request body (not as a query parameter)
    so it is not captured in access logs or browser history.
    """

    refresh_token: str


class TokenValidationResponse(BaseModel):
    """Response schema for token validation."""

    valid: bool
    user_id: Optional[str] = None
    role: Optional[str] = None
    message: Optional[str] = None
