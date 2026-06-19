"""Authentication router — login, register, logout, refresh, password reset."""

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import get_current_user
from app.models.token import RefreshTokenRequest, TokenResponse
from app.models.user import (
    PasswordReset,
    PasswordResetRequest,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate):
    """Register a new user account."""
    return auth_service.register(user_data)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Authenticate user and return JWT tokens."""
    return auth_service.login(credentials)


@router.post("/logout", status_code=204)
async def logout(current_user: dict = Depends(get_current_user)):
    """Invalidate current user sessions."""
    auth_service.logout(current_user["user_id"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh an expired access token."""
    return auth_service.refresh_token(request.refresh_token)


@router.post("/password/reset-request", status_code=204)
async def request_password_reset(request: PasswordResetRequest):
    """Initiate password reset (sends email)."""
    auth_service.request_password_reset(request.email)


@router.post("/password/reset", status_code=204)
async def reset_password(request: PasswordReset):
    """Complete password reset with token."""
    auth_service.reset_password(request.token, request.new_password)
