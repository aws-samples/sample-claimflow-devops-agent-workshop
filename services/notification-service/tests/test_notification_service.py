"""Tests for notification service business logic."""

import pytest
from unittest.mock import patch, MagicMock

from app.models.notification import SendNotificationRequest, PreferencesUpdate
from app.services.notification_service import NotificationService


@pytest.fixture
def notification_service():
    """Create NotificationService with mocked dependencies."""
    with patch("app.services.notification_service.NotificationRepository") as mock_repo, \
         patch("app.services.notification_service.SESClient") as mock_ses, \
         patch("app.services.notification_service.SNSClient") as mock_sns, \
         patch("app.services.notification_service.TemplateService") as mock_templates:
        service = NotificationService()
        service.repo = mock_repo.return_value
        service.ses = mock_ses.return_value
        service.sns = mock_sns.return_value
        service.templates = mock_templates.return_value
        yield service


def test_send_notification_email_only(notification_service):
    """Sending notification with email enabled should send via SES."""
    notification_service.repo.get_preferences.return_value = {
        "user_id": "user1",
        "email_enabled": True,
        "sms_enabled": False,
        "email_address": "user@example.com",
    }
    notification_service.templates.get_email_subject.return_value = "Status Changed"
    notification_service.templates.get_email_body.return_value = "Your claim status changed."
    notification_service.ses.send_email.return_value = {"message_id": "msg-123", "success": True}
    notification_service.repo.save_notification_log.return_value = {
        "notification_id": "notif-123",
        "sent_at": "2025-05-25T00:00:00Z",
    }

    request = SendNotificationRequest(
        user_id="user1",
        claim_id="claim-456",
        event_type="claim_status_change",
        status="approved",
    )

    result = notification_service.send_notification(request)

    assert result.notification_id == "notif-123"
    assert "email" in result.channels_sent
    assert "sms" not in result.channels_sent
    assert result.success is True
    notification_service.ses.send_email.assert_called_once()


def test_send_notification_both_channels(notification_service):
    """Sending notification with both channels enabled should send via SES and SNS."""
    notification_service.repo.get_preferences.return_value = {
        "user_id": "user1",
        "email_enabled": True,
        "sms_enabled": True,
        "email_address": "user@example.com",
        "phone_number": "+1234567890",
    }
    notification_service.templates.get_email_subject.return_value = "Approved"
    notification_service.templates.get_email_body.return_value = "Your claim was approved."
    notification_service.templates.get_sms_message.return_value = "Claim approved."
    notification_service.ses.send_email.return_value = {"message_id": "msg-1", "success": True}
    notification_service.sns.send_sms.return_value = {"message_id": "msg-2", "success": True}
    notification_service.repo.save_notification_log.return_value = {
        "notification_id": "notif-456",
        "sent_at": "2025-05-25T00:00:00Z",
    }

    request = SendNotificationRequest(
        user_id="user1",
        claim_id="claim-789",
        event_type="claim_approved",
        status="approved",
    )

    result = notification_service.send_notification(request)

    assert "email" in result.channels_sent
    assert "sms" in result.channels_sent
    assert result.success is True


def test_send_notification_no_preferences(notification_service):
    """Sending notification with no preferences should not send anything."""
    notification_service.repo.get_preferences.return_value = None
    notification_service.repo.save_notification_log.return_value = {
        "notification_id": "notif-789",
        "sent_at": "2025-05-25T00:00:00Z",
    }

    request = SendNotificationRequest(
        user_id="user1",
        claim_id="claim-101",
        event_type="claim_rejected",
        status="rejected",
    )

    result = notification_service.send_notification(request)

    assert result.channels_sent == []
    assert result.success is False


def test_get_preferences_default(notification_service):
    """Getting preferences for user with no saved preferences should return defaults."""
    notification_service.repo.get_preferences.return_value = None

    result = notification_service.get_preferences("user1")

    assert result.user_id == "user1"
    assert result.email_enabled is True
    assert result.sms_enabled is False


def test_update_preferences(notification_service):
    """Updating preferences should save and return updated values."""
    notification_service.repo.get_preferences.return_value = {
        "user_id": "user1",
        "email_enabled": True,
        "sms_enabled": False,
    }
    notification_service.repo.update_preferences.return_value = {
        "user_id": "user1",
        "email_enabled": True,
        "sms_enabled": True,
        "phone_number": "+1234567890",
    }

    updates = PreferencesUpdate(sms_enabled=True, phone_number="+1234567890")
    result = notification_service.update_preferences("user1", updates)

    assert result.sms_enabled is True
    assert result.phone_number == "+1234567890"
