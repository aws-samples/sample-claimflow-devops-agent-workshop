"""Amazon SNS integration — Publish for SMS notifications."""

import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class SNSClient:
    """Client for Amazon SNS SMS delivery."""

    def __init__(self):
        self.client = boto3.client("sns", region_name=settings.aws_region)

    def send_sms(self, phone_number: str, message: str) -> dict:
        """Send an SMS via SNS.

        Args:
            phone_number: Recipient phone number (E.164 format).
            message: SMS message text.

        Returns:
            dict with 'message_id' and 'success' keys.
        """
        try:
            response = self.client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",
                    }
                },
            )

            message_id = response.get("MessageId", "")
            logger.info(f"SMS sent, MessageId: {message_id}")

            return {"message_id": message_id, "success": True}

        except Exception as e:
            logger.error(f"SNS Publish failed: {e}")
            return {"message_id": "", "success": False, "error": str(e)}
