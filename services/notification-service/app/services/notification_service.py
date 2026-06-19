"""Notification service — orchestrates sending notifications."""

import logging
from typing import Optional

from app.models.notification import (
    NotificationLogEntry,
    NotificationResponse,
    PreferencesResponse,
    PreferencesUpdate,
    SendNotificationRequest,
)
from app.repositories.notification_repository import NotificationRepository
from app.services.ses_client import SESClient
from app.services.sns_client import SNSClient
from app.services.template_service import TemplateService

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles notification orchestration and delivery."""

    def __init__(self):
        self.repo = NotificationRepository()
        self.ses = SESClient()
        self.sns = SNSClient()
        self.templates = TemplateService()

    def send_notification(self, request: SendNotificationRequest) -> NotificationResponse:
        """Send notification via configured channels based on user preferences."""
        # Get user preferences
        preferences = self.repo.get_preferences(request.user_id)
        channels_sent = []

        template_vars = {
            "claim_id": request.claim_id,
            "status": request.status,
        }

        # Send email if enabled
        if preferences and preferences.get("email_enabled", True) and preferences.get("email_address"):
            email_result = self._send_email(
                to_email=preferences["email_address"],
                event_type=request.event_type,
                template_vars=template_vars,
                user_id=request.user_id,
                claim_id=request.claim_id,
            )
            if email_result:
                channels_sent.append("email")

        # Send SMS if enabled
        if preferences and preferences.get("sms_enabled", False) and preferences.get("phone_number"):
            sms_result = self._send_sms(
                phone_number=preferences["phone_number"],
                event_type=request.event_type,
                template_vars=template_vars,
                user_id=request.user_id,
                claim_id=request.claim_id,
            )
            if sms_result:
                channels_sent.append("sms")

        # Log the notification
        log_data = {
            "user_id": request.user_id,
            "claim_id": request.claim_id,
            "event_type": request.event_type,
            "channels_sent": channels_sent,
            "success": len(channels_sent) > 0,
        }
        saved = self.repo.save_notification_log(log_data)

        return NotificationResponse(
            notification_id=saved["notification_id"],
            user_id=request.user_id,
            claim_id=request.claim_id,
            event_type=request.event_type,
            channels_sent=channels_sent,
            sent_at=saved["sent_at"],
            success=len(channels_sent) > 0,
        )

    def get_preferences(self, user_id: str) -> PreferencesResponse:
        """Get notification preferences for a user."""
        preferences = self.repo.get_preferences(user_id)

        if not preferences:
            # Return defaults
            return PreferencesResponse(
                user_id=user_id,
                email_enabled=True,
                sms_enabled=False,
            )

        return PreferencesResponse(
            user_id=preferences["user_id"],
            email_enabled=preferences.get("email_enabled", True),
            sms_enabled=preferences.get("sms_enabled", False),
            email_address=preferences.get("email_address"),
            phone_number=preferences.get("phone_number"),
        )

    def update_preferences(self, user_id: str, updates: PreferencesUpdate) -> PreferencesResponse:
        """Update notification preferences for a user."""
        existing = self.repo.get_preferences(user_id)

        if existing:
            update_dict = updates.model_dump(exclude_none=True)
            updated = self.repo.update_preferences(user_id, update_dict)
        else:
            # Create new preferences
            pref_data = {
                "user_id": user_id,
                "email_enabled": updates.email_enabled if updates.email_enabled is not None else True,
                "sms_enabled": updates.sms_enabled if updates.sms_enabled is not None else False,
                "email_address": updates.email_address,
                "phone_number": updates.phone_number,
            }
            updated = self.repo.save_preferences(pref_data)

        return PreferencesResponse(
            user_id=updated["user_id"],
            email_enabled=updated.get("email_enabled", True),
            sms_enabled=updated.get("sms_enabled", False),
            email_address=updated.get("email_address"),
            phone_number=updated.get("phone_number"),
        )

    def get_notification_logs(
        self,
        user_id: Optional[str] = None,
        claim_id: Optional[str] = None,
    ) -> list[dict]:
        """Get notification logs filtered by user_id and/or claim_id."""
        return self.repo.get_notification_logs(user_id=user_id, claim_id=claim_id)

    def _send_email(
        self,
        to_email: str,
        event_type: str,
        template_vars: dict,
        user_id: str,
        claim_id: str,
    ) -> bool:
        """Send email notification."""
        try:
            subject = self.templates.get_email_subject(event_type, **template_vars)
            body = self.templates.get_email_body(event_type, **template_vars)

            result = self.ses.send_email(to_email, subject, body)
            return result.get("success", False)

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _send_sms(
        self,
        phone_number: str,
        event_type: str,
        template_vars: dict,
        user_id: str,
        claim_id: str,
    ) -> bool:
        """Send SMS notification."""
        try:
            message = self.templates.get_sms_message(event_type, **template_vars)

            result = self.sns.send_sms(phone_number, message)
            return result.get("success", False)

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
