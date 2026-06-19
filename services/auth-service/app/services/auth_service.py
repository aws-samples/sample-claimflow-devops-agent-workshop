"""Authentication service — login, register, token validation, password reset."""

from typing import Optional

from fastapi import HTTPException, status

from app.models.token import TokenResponse, TokenType, TokenValidationResponse
from app.models.user import UserCreate, UserLogin, UserResponse
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.password_service import hash_password, verify_password
from app.services.token_service import (
    create_password_reset_token,
    create_token_pair,
    decode_token,
)


class AuthService:
    """Handles authentication workflows."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.session_repo = SessionRepository()

    def register(self, user_data: UserCreate) -> UserResponse:
        """Register a new user."""
        # Check if email already exists
        existing = self.user_repo.get_user_by_email(user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user_dict = user_data.model_dump()
        user_dict["password_hash"] = hash_password(user_dict.pop("password"))
        user_dict["role"] = user_dict["role"].value

        try:
            created = self.user_repo.create_user(user_dict)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User ID already exists",
            )

        return UserResponse(
            user_id=created["user_id"],
            email=created["email"],
            full_name=created["full_name"],
            phone=created.get("phone"),
            role=created["role"],
            status=created["status"],
            created_at=created["created_at"],
        )

    def login(self, credentials: UserLogin) -> TokenResponse:
        """Authenticate user and return tokens."""
        user = self.user_repo.get_user_by_id(credentials.user_id)

        if not user or not verify_password(credentials.password, user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if user.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        # Create tokens
        token_response = create_token_pair(user["user_id"], user["role"])

        # Create session
        self.session_repo.create_session(user["user_id"], token_response.refresh_token)

        # Update last login
        self.user_repo.update_last_login(user["user_id"])

        return token_response

    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh an expired access token."""
        payload = decode_token(refresh_token)

        if not payload or payload.token_type != TokenType.REFRESH.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify session exists
        session = self.session_repo.get_session_by_token(payload.sub, refresh_token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found or expired",
            )

        # Invalidate old session and create new tokens
        self.session_repo.invalidate_session(session["session_id"])
        token_response = create_token_pair(payload.sub, payload.role)
        self.session_repo.create_session(payload.sub, token_response.refresh_token)

        return token_response

    def logout(self, user_id: str) -> None:
        """Invalidate all sessions for the user."""
        self.session_repo.invalidate_all_user_sessions(user_id)

    def validate_token(self, token: str) -> TokenValidationResponse:
        """Validate a token (used by other services)."""
        payload = decode_token(token)

        if not payload or payload.token_type != TokenType.ACCESS.value:
            return TokenValidationResponse(valid=False, message="Invalid or expired token")

        return TokenValidationResponse(
            valid=True,
            user_id=payload.sub,
            role=payload.role,
        )

    def request_password_reset(self, email: str) -> None:
        """Initiate password reset — generate token and send email."""
        user = self.user_repo.get_user_by_email(email)
        if not user:
            # Don't reveal whether email exists
            return

        reset_token = create_password_reset_token(user["user_id"])
        # In production, send email via SES with reset link
        # For now, log the token (email sending handled by utils/email_client.py)

    def reset_password(self, token: str, new_password: str) -> None:
        """Complete password reset with token."""
        payload = decode_token(token)

        if not payload or payload.token_type != TokenType.PASSWORD_RESET.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        password_hash = hash_password(new_password)
        self.user_repo.update_user(payload.sub, {"password_hash": password_hash})

        # Invalidate all existing sessions
        self.session_repo.invalidate_all_user_sessions(payload.sub)
