"""User data models and schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles for RBAC."""

    POLICYHOLDER = "policyholder"
    ADJUDICATOR = "adjudicator"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class UserCreate(BaseModel):
    """Request schema for user registration."""

    user_id: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = None
    role: UserRole = UserRole.POLICYHOLDER


class UserLogin(BaseModel):
    """Request schema for user login."""

    user_id: str
    password: str


class UserResponse(BaseModel):
    """Response schema for user data."""

    user_id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    status: UserStatus
    created_at: str
    last_login: Optional[str] = None


class UserUpdate(BaseModel):
    """Request schema for updating user profile."""

    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Request schema for initiating password reset."""

    email: str


class PasswordReset(BaseModel):
    """Request schema for completing password reset."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
