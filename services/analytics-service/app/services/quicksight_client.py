"""QuickSight client — generate authenticated embed URLs."""

import logging
from datetime import datetime, timezone, timedelta

import boto3

from app.config import settings
from app.models.analytics import DashboardUrlResponse

logger = logging.getLogger(__name__)


class QuickSightClient:
    """Handles Amazon QuickSight dashboard embedding."""

    def __init__(self):
        self.client = boto3.client("quicksight", region_name=settings.aws_region)

    def generate_embed_url(self, user_arn: str) -> DashboardUrlResponse:
        """Generate an authenticated embed URL for a registered QuickSight user.

        Args:
            user_arn: The ARN of the registered QuickSight user.

        Returns:
            DashboardUrlResponse with the embed URL and expiration time.
        """
        try:
            response = self.client.generate_embed_url_for_registered_user(
                AwsAccountId=settings.quicksight_account_id,
                UserArn=user_arn,
                SessionLifetimeInMinutes=60,
                ExperienceConfiguration={
                    "Dashboard": {
                        "InitialDashboardId": settings.quicksight_dashboard_id,
                    }
                },
            )

            embed_url = response["EmbedUrl"]
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)

            logger.info("Generated QuickSight embed URL successfully")
            return DashboardUrlResponse(url=embed_url, expires_at=expires_at)

        except Exception as e:
            logger.warning(f"Failed to generate QuickSight embed URL: {e}")
            raise
