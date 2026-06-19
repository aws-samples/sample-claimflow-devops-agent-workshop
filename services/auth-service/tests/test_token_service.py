"""Tests for JWT token creation and validation."""

from app.models.token import BEARER_SCHEME, TokenType
from app.services.token_service import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
)


def test_create_access_token():
    """Access token should be decodable with correct claims."""
    token = create_access_token("user123", "policyholder")
    payload = decode_token(token)

    assert payload is not None
    assert payload.sub == "user123"
    assert payload.role == "policyholder"
    assert payload.token_type == TokenType.ACCESS.value


def test_create_refresh_token():
    """Refresh token should be decodable with correct claims."""
    token = create_refresh_token("user123", "admin")
    payload = decode_token(token)

    assert payload is not None
    assert payload.sub == "user123"
    assert payload.role == "admin"
    assert payload.token_type == TokenType.REFRESH.value


def test_create_token_pair():
    """Token pair should contain both access and refresh tokens."""
    response = create_token_pair("user123", "adjudicator")

    assert response.access_token is not None
    assert response.refresh_token is not None
    assert response.token_type == BEARER_SCHEME
    assert response.expires_in > 0


def test_decode_invalid_token():
    """Invalid token should return None."""
    payload = decode_token("invalid.token.here")
    assert payload is None


def test_decode_empty_token():
    """Empty token should return None."""
    payload = decode_token("")
    assert payload is None
