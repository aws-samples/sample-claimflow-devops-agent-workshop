"""Analytics router — dashboard, metrics, and data sync endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import require_role
from app.models.analytics import (
    DashboardUrlResponse,
    MetricsSummaryResponse,
    SyncStatusResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.quicksight_client import QuickSightClient

router = APIRouter()
analytics_service = AnalyticsService()
quicksight_client = QuickSightClient()


@router.get("/dashboard", response_model=DashboardUrlResponse)
async def get_dashboard(
    current_user: dict = Depends(require_role("admin", "adjudicator")),
):
    """Get QuickSight embedded dashboard URL (admin/adjudicator only)."""
    user_arn = (
        f"arn:aws:quicksight:us-east-1:"
        f"{quicksight_client.client.meta.config.user_agent}:"
        f"user/default/{current_user['user_id']}"
    )
    return quicksight_client.generate_embed_url(user_arn)


@router.get("/metrics", response_model=MetricsSummaryResponse)
async def get_metrics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    claim_type: Optional[str] = None,
    current_user: dict = Depends(require_role("admin", "adjudicator")),
):
    """Get aggregated claims metrics (admin/adjudicator only).

    Query parameters:
        date_from: Filter claims submitted on or after this date (ISO format).
        date_to: Filter claims submitted on or before this date (ISO format).
        claim_type: Filter by claim type (e.g., auto, health, property).
    """
    return analytics_service.get_metrics(
        date_from=date_from,
        date_to=date_to,
        claim_type=claim_type,
    )


@router.post("/sync", response_model=SyncStatusResponse)
async def trigger_sync(
    current_user: dict = Depends(require_role("admin")),
):
    """Trigger data sync from DynamoDB to Aurora PostgreSQL (admin only)."""
    return analytics_service.trigger_sync()
