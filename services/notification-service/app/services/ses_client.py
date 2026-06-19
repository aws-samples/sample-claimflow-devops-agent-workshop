"""Amazon SES integration — SendEmail for email notifications."""

import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class SESClient:
    """Client for Amazon SES email delivery."""

    def __init__(self):
        self.client = boto3.client("ses", region_name=settings.aws_region)
        self.sender_email = settings.ses_sender_email

    def send_email(self, to_email: str, subject: str, body: str) -> dict:
        """Send an email via SES.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            body: Email body text.

        Returns:
            dict with 'message_id' and 'success' keys.
        """
        try:
            response = self.client.send_email(
                Source=self.sender_email,
                Destination={
                    "ToAddresses": [to_email],
                },
                Message={
                    "Subject": {
                        "Data": subject,
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Text": {
                            "Data": body,
                            "Charset": "UTF-8",
                        },
                    },
                },
            )

            message_id = response.get("MessageId", "")
            logger.info(f"Email sent to {to_email}, MessageId: {message_id}")

            return {"message_id": message_id, "success": True}

        except Exception as e:
            logger.error(f"SES SendEmail failed for {to_email}: {e}")
            return {"message_id": "", "success": False, "error": str(e)}
