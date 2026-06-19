"""User management service — CRUD, role assignment, deactivation."""

from typing import Optional

from fastapi import HTTPException, status

from app.models.user import UserResponse, UserRole, UserUpdate
from app.repositories.user_repository import UserRepository


class UserService:
    """Handles user management operations (admin functions)."""

    def __init__(self):
        self.user_repo = UserRepository()

    def get_user(self, user_id: str) -> UserResponse:
        """Get user by ID."""
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return self._to_response(user)

    def list_users(
        self, role: Optional[str] = None, status_filter: Optional[str] = None
    ) -> list[UserResponse]:
        """List users with optional filtering."""
        users = self.user_repo.list_users(role=role, status=status_filter)
        return [self._to_response(u) for u in users]

    def update_user(self, user_id: str, updates: UserUpdate) -> UserResponse:
        """Update user profile."""
        update_dict = updates.model_dump(exclude_none=True)
        if not update_dict:
            return self.get_user(user_id)

        updated = self.user_repo.update_user(user_id, update_dict)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return self._to_response(updated)

    def update_role(self, user_id: str, new_role: UserRole) -> UserResponse:
        """Change user role (admin only)."""
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        updated = self.user_repo.update_user(user_id, {"role": new_role.value})
        return self._to_response(updated)

    def deactivate_user(self, user_id: str, admin_user_id: str) -> None:
        """Deactivate a user account."""
        if user_id == admin_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )

        # Check if this is the last admin
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.get("role") == "admin":
            admins = self.user_repo.list_users(role="admin", status="active")
            if len(admins) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last admin account",
                )

        self.user_repo.deactivate_user(user_id)

    def _to_response(self, user: dict) -> UserResponse:
        """Convert DynamoDB item to UserResponse."""
        return UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user["full_name"],
            phone=user.get("phone"),
            role=user["role"],
            status=user["status"],
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
