"""Analytics service — compute metrics and trigger data sync."""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.analytics import MetricsSummaryResponse, SyncStatusResponse
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Handles metrics computation and data synchronization."""

    def __init__(self):
        self.repository = AnalyticsRepository()
        self._last_sync_at: Optional[datetime] = None
        self._last_sync_count: int = 0

    def get_metrics(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        claim_type: Optional[str] = None,
    ) -> MetricsSummaryResponse:
        """Compute and return aggregated metrics."""
        metrics = self.repository.get_metrics(
            date_from=date_from,
            date_to=date_to,
            claim_type=claim_type,
        )
        return MetricsSummaryResponse(**metrics)

    def trigger_sync(self) -> SyncStatusResponse:
        """Trigger data sync from DynamoDB to Aurora PostgreSQL."""
        try:
            claims = self.repository.scan_claims_from_dynamodb()
            records_synced = self.repository.sync_to_aurora(claims)
            self._last_sync_at = datetime.now(timezone.utc)
            self._last_sync_count = records_synced

            logger.info(f"Sync completed: {records_synced} records synced")
            return SyncStatusResponse(
                status="completed",
                records_synced=records_synced,
                last_sync_at=self._last_sync_at,
            )
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return SyncStatusResponse(
                status="failed",
                records_synced=0,
                last_sync_at=self._last_sync_at,
            )

    def get_sync_status(self) -> SyncStatusResponse:
        """Return the status of the last sync operation."""
        return SyncStatusResponse(
            status="idle" if self._last_sync_at else "never_run",
            records_synced=self._last_sync_count,
            last_sync_at=self._last_sync_at,
        )
