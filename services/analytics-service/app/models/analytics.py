"""Analytics response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MetricsSummaryResponse(BaseModel):
    """Aggregated claims metrics summary."""

    total_claims: int
    approved_count: int
    rejected_count: int
    pending_count: int
    avg_processing_time_hours: float
    fraud_detection_rate: float
    approval_rate: float


class DashboardUrlResponse(BaseModel):
    """QuickSight embedded dashboard URL."""

    url: str
    expires_at: datetime


class SyncStatusResponse(BaseModel):
    """Data sync operation status."""

    status: str
    records_synced: int
    last_sync_at: Optional[datetime] = None
