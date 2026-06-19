"""Template service — notification templates per event type."""

import logging

logger = logging.getLogger(__name__)


# Notification templates keyed by event_type
TEMPLATES = {
    "claim_status_change": {
        "subject": "Your Claim Status Has Changed",
        "body": (
            "Dear Policyholder,\n\n"
            "Your claim (ID: {claim_id}) status has been updated to: {status}.\n\n"
            "Please log in to your account to view the details.\n\n"
            "Best regards,\n"
            "Claims Processing Team"
        ),
        "sms": "Your claim {claim_id} status changed to: {status}. Log in for details.",
    },
    "claim_approved": {
        "subject": "Your Claim Has Been Approved",
        "body": (
            "Dear Policyholder,\n\n"
            "Great news! Your claim (ID: {claim_id}) has been approved.\n\n"
            "Settlement details will be processed shortly. "
            "Please log in to your account for more information.\n\n"
            "Best regards,\n"
            "Claims Processing Team"
        ),
        "sms": "Good news! Your claim {claim_id} has been approved. Check your account for details.",
    },
    "claim_rejected": {
        "subject": "Your Claim Decision",
        "body": (
            "Dear Policyholder,\n\n"
            "After careful review, your claim (ID: {claim_id}) could not be approved at this time.\n\n"
            "Please log in to your account to view the detailed explanation "
            "and information about the appeals process.\n\n"
            "Best regards,\n"
            "Claims Processing Team"
        ),
        "sms": "Your claim {claim_id} has been reviewed. Please log in for details.",
    },
}


class TemplateService:
    """Renders notification templates."""

    def get_email_subject(self, event_type: str, **kwargs) -> str:
        """Get the email subject for an event type."""
        template = TEMPLATES.get(event_type)
        if not template:
            return f"Notification: {event_type}"
        return template["subject"]

    def get_email_body(self, event_type: str, **kwargs) -> str:
        """Get the rendered email body for an event type."""
        template = TEMPLATES.get(event_type)
        if not template:
            return f"You have a new notification regarding your claim."

        try:
            return template["body"].format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template["body"]

    def get_sms_message(self, event_type: str, **kwargs) -> str:
        """Get the rendered SMS message for an event type."""
        template = TEMPLATES.get(event_type)
        if not template:
            return f"You have a new notification. Please check your account."

        try:
            return template["sms"].format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template["sms"]
