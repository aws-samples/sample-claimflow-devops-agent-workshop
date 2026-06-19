"""Email client for sending emails via Amazon SES."""

import boto3
from botocore.exceptions import ClientError

from app.config import settings


class EmailClient:
    """Send emails via Amazon SES."""

    def __init__(self):
        self.ses_client = boto3.client("ses", region_name=settings.aws_region)
        self.sender = settings.ses_sender_email

    def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email with token link."""
        subject = "Claim Processing - Password Reset Request"
        body_html = f"""
        <html>
        <body>
            <h2>Password Reset</h2>
            <p>You requested a password reset for your Claim Processing account.</p>
            <p>Use the following token to reset your password:</p>
            <p><strong>{reset_token}</strong></p>
            <p>This token expires in 1 hour.</p>
            <p>If you did not request this reset, please ignore this email.</p>
        </body>
        </html>
        """

        try:
            self.ses_client.send_email(
                Source=self.sender,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Html": {"Data": body_html}},
                },
            )
            return True
        except ClientError:
            return False
