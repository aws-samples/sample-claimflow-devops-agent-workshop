"""Tests for analytics service (unit tests with mocked repository)."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.services.analytics_service import AnalyticsService
from app.models.analytics import MetricsSummaryResponse, SyncStatusResponse


@pytest.fixture
def analytics_service():
    """Create AnalyticsService with mocked repository."""
    with patch(
        "app.services.analytics_service.AnalyticsRepository"
    ) as mock_repo_class:
        service = AnalyticsService()
        service.repository = mock_repo_class.return_value
        yield service


def test_get_metrics_returns_summary(analytics_service):
    """get_metrics should return a MetricsSummaryResponse with correct values."""
    analytics_service.repository.get_metrics.return_value = {
        "total_claims": 100,
        "approved_count": 60,
        "rejected_count": 20,
        "pending_count": 20,
        "avg_processing_time_hours": 24.5,
        "fraud_detection_rate": 0.15,
        "approval_rate": 0.60,
    }

    result = analytics_service.get_metrics(date_from="2025-01-01", date_to="2025-06-01")

    assert isinstance(result, MetricsSummaryResponse)
    assert result.total_claims == 100
    assert result.approved_count == 60
    assert result.rejected_count == 20
    assert result.pending_count == 20
    assert result.avg_processing_time_hours == 24.5
    assert result.fraud_detection_rate == 0.15
    assert result.approval_rate == 0.60
    analytics_service.repository.get_metrics.assert_called_once_with(
        date_from="2025-01-01", date_to="2025-06-01", claim_type=None
    )


def test_get_metrics_with_claim_type_filter(analytics_service):
    """get_metrics should pass claim_type filter to repository."""
    analytics_service.repository.get_metrics.return_value = {
        "total_claims": 30,
        "approved_count": 20,
        "rejected_count": 5,
        "pending_count": 5,
        "avg_processing_time_hours": 12.0,
        "fraud_detection_rate": 0.10,
        "approval_rate": 0.67,
    }

    result = analytics_service.get_metrics(claim_type="auto")

    assert result.total_claims == 30
    analytics_service.repository.get_metrics.assert_called_once_with(
        date_from=None, date_to=None, claim_type="auto"
    )


def test_trigger_sync_success(analytics_service):
    """trigger_sync should return completed status with record count."""
    analytics_service.repository.scan_claims_from_dynamodb.return_value = [
        {"claim_id": "CLM-001", "status": "approved"},
        {"claim_id": "CLM-002", "status": "pending"},
        {"claim_id": "CLM-003", "status": "rejected"},
    ]
    analytics_service.repository.sync_to_aurora.return_value = 3

    result = analytics_service.trigger_sync()

    assert isinstance(result, SyncStatusResponse)
    assert result.status == "completed"
    assert result.records_synced == 3
    assert result.last_sync_at is not None
    analytics_service.repository.scan_claims_from_dynamodb.assert_called_once()
    analytics_service.repository.sync_to_aurora.assert_called_once()


def test_trigger_sync_failure(analytics_service):
    """trigger_sync should return failed status on exception."""
    analytics_service.repository.scan_claims_from_dynamodb.side_effect = Exception(
        "DynamoDB connection error"
    )

    result = analytics_service.trigger_sync()

    assert result.status == "failed"
    assert result.records_synced == 0
