"""Notification router — notification management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import get_current_user
from app.models.notification import (
    NotificationResponse,
    PreferencesResponse,
    PreferencesUpdate,
    SendNotificationRequest,
)
from app.services.notification_service import NotificationService

router = APIRouter()
notification_service = NotificationService()


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a notification to a user via configured channels."""
    return notification_service.send_notification(request)


@router.get("/preferences/{user_id}", response_model=PreferencesResponse)
async def get_preferences(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get notification preferences for a user."""
    return notification_service.get_preferences(user_id)


@router.put("/preferences/{user_id}", response_model=PreferencesResponse)
async def update_preferences(
    user_id: str,
    updates: PreferencesUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update notification preferences for a user."""
    return notification_service.update_preferences(user_id, updates)


@router.get("/log")
async def get_notification_log(
    user_id: Optional[str] = Query(None),
    claim_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get notification log entries filtered by user_id and/or claim_id."""
    return notification_service.get_notification_logs(user_id=user_id, claim_id=claim_id)
