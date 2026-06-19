"""Tests for authentication service (integration-style with mocked DynamoDB)."""

import secrets

import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from app.models.token import BEARER_SCHEME
from app.models.user import UserCreate, UserLogin, UserRole
from app.services.auth_service import AuthService


def _make_password() -> str:
    """Generate a random password for tests (no hardcoded credentials)."""
    return secrets.token_urlsafe(12)


@pytest.fixture
def auth_service():
    """Create AuthService with mocked repositories."""
    with patch("app.services.auth_service.UserRepository") as mock_user_repo, \
         patch("app.services.auth_service.SessionRepository") as mock_session_repo:
        service = AuthService()
        service.user_repo = mock_user_repo.return_value
        service.session_repo = mock_session_repo.return_value
        yield service


def test_register_success(auth_service):
    """Successful registration should return user response."""
    auth_service.user_repo.get_user_by_email.return_value = None
    auth_service.user_repo.create_user.return_value = {
        "user_id": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "phone": None,
        "role": "policyholder",
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
    }

    user_data = UserCreate(
        user_id="testuser",
        email="test@example.com",
        password=_make_password(),
        full_name="Test User",
    )

    result = auth_service.register(user_data)
    assert result.user_id == "testuser"
    assert result.email == "test@example.com"
    assert result.role == "policyholder"


def test_register_duplicate_email(auth_service):
    """Registration with existing email should raise 409."""
    auth_service.user_repo.get_user_by_email.return_value = {"user_id": "existing"}

    user_data = UserCreate(
        user_id="newuser",
        email="existing@example.com",
        password=_make_password(),
        full_name="New User",
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.register(user_data)
    assert exc_info.value.status_code == 409


def test_login_success(auth_service):
    """Successful login should return token response."""
    from app.services.password_service import hash_password

    password = _make_password()
    auth_service.user_repo.get_user_by_id.return_value = {
        "user_id": "testuser",
        "password_hash": hash_password(password),
        "role": "policyholder",
        "status": "active",
    }
    auth_service.session_repo.create_session.return_value = {}

    credentials = UserLogin(user_id="testuser", password=password)
    result = auth_service.login(credentials)

    assert result.access_token is not None
    assert result.refresh_token is not None
    assert result.token_type == BEARER_SCHEME


def test_login_invalid_credentials(auth_service):
    """Login with wrong password should raise 401."""
    from app.services.password_service import hash_password

    auth_service.user_repo.get_user_by_id.return_value = {
        "user_id": "testuser",
        "password_hash": hash_password(_make_password()),
        "role": "policyholder",
        "status": "active",
    }

    credentials = UserLogin(user_id="testuser", password=_make_password())

    with pytest.raises(HTTPException) as exc_info:
        auth_service.login(credentials)
    assert exc_info.value.status_code == 401


def test_login_inactive_user(auth_service):
    """Login with inactive account should raise 403."""
    from app.services.password_service import hash_password

    password = _make_password()
    auth_service.user_repo.get_user_by_id.return_value = {
        "user_id": "testuser",
        "password_hash": hash_password(password),
        "role": "policyholder",
        "status": "inactive",
    }

    credentials = UserLogin(user_id="testuser", password=password)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.login(credentials)
    assert exc_info.value.status_code == 403


def test_validate_token_valid(auth_service):
    """Valid access token should return valid response."""
    from app.services.token_service import create_access_token

    token = create_access_token("user123", "admin")
    result = auth_service.validate_token(token)

    assert result.valid is True
    assert result.user_id == "user123"
    assert result.role == "admin"


def test_validate_token_invalid(auth_service):
    """Invalid token should return invalid response."""
    result = auth_service.validate_token("invalid.token")

    assert result.valid is False
    assert result.user_id is None
