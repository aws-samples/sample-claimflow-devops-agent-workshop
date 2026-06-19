"""Notification data models and schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class SendNotificationRequest(BaseModel):
    """Request schema for sending a notification."""

    user_id: str = Field(..., min_length=1)
    claim_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)


class NotificationResponse(BaseModel):
    """Response schema for notification send result."""

    notification_id: str
    user_id: str
    claim_id: str
    event_type: str
    channels_sent: list[str] = []
    sent_at: str
    success: bool


class NotificationLogEntry(BaseModel):
    """A single notification log entry."""

    notification_id: str
    user_id: str
    claim_id: str
    event_type: str
    channel: str
    status: str
    sent_at: str
    error_message: Optional[str] = None


class PreferencesResponse(BaseModel):
    """Response schema for notification preferences."""

    user_id: str
    email_enabled: bool = True
    sms_enabled: bool = False
    email_address: Optional[str] = None
    phone_number: Optional[str] = None


class PreferencesUpdate(BaseModel):
    """Request schema for updating notification preferences."""

    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
