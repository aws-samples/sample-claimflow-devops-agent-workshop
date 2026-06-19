"""User management router — CRUD, role assignment, deactivation (admin only)."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import get_current_user, require_role
from app.models.user import UserResponse, UserRole, UserUpdate
from app.services.user_service import UserService

router = APIRouter()
user_service = UserService()


@router.get("", response_model=list[UserResponse])
async def list_users(
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_role("admin")),
):
    """List all users with optional filtering (admin only)."""
    return user_service.list_users(role=role, status_filter=status)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get user profile (admin or self)."""
    if current_user["role"] != "admin" and current_user["user_id"] != user_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user_service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    updates: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update user profile (admin or self)."""
    if current_user["role"] != "admin" and current_user["user_id"] != user_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return user_service.update_user(user_id, updates)


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role: UserRole,
    current_user: dict = Depends(require_role("admin")),
):
    """Change user role (admin only)."""
    return user_service.update_role(user_id, role)


@router.put("/{user_id}/deactivate", status_code=204)
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    """Deactivate a user account (admin only)."""
    user_service.deactivate_user(user_id, current_user["user_id"])
