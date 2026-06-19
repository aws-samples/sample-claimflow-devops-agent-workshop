"""Tests for fraud service business logic."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from app.models.fraud import FraudAnalysisRequest, RiskLevel
from app.services.fraud_service import FraudService


@pytest.fixture
def fraud_service():
    """Create FraudService with mocked dependencies."""
    with patch("app.services.fraud_service.FraudRepository") as mock_repo, \
         patch("app.services.fraud_service.BedrockClient") as mock_bedrock:
        service = FraudService()
        service.repo = mock_repo.return_value
        service.bedrock = mock_bedrock.return_value
        yield service


def test_analyze_claim_low_risk(fraud_service):
    """Analyzing a low-risk claim should return low score."""
    fraud_service.bedrock.analyze_claim_for_fraud.return_value = {
        "score": 15,
        "risk_level": "Low",
        "explanation": "No fraud indicators detected.",
        "indicators": [],
    }
    fraud_service.repo.save_fraud_score.return_value = {
        "claim_id": "claim-123",
        "score": 15,
        "risk_level": "Low",
        "explanation": "No fraud indicators detected.",
        "indicators": [],
        "analyzed_at": "2025-05-25T00:00:00Z",
    }

    request = FraudAnalysisRequest(
        claim_id="claim-123",
        claim_type="health",
        amount=500.0,
        description="Routine checkup",
        user_id="user1",
        policy_number="POL-001",
    )

    result = fraud_service.analyze_claim(request)

    assert result.score == 15
    assert result.risk_level == RiskLevel.LOW
    assert result.claim_id == "claim-123"


def test_analyze_claim_high_risk_saves_pattern(fraud_service):
    """Analyzing a high-risk claim should save a fraud pattern."""
    fraud_service.bedrock.analyze_claim_for_fraud.return_value = {
        "score": 85,
        "risk_level": "High",
        "explanation": "Multiple fraud indicators detected.",
        "indicators": ["Unusually high amount", "Suspicious timing"],
    }
    fraud_service.repo.save_fraud_score.return_value = {
        "claim_id": "claim-456",
        "score": 85,
        "risk_level": "High",
        "explanation": "Multiple fraud indicators detected.",
        "indicators": ["Unusually high amount", "Suspicious timing"],
        "analyzed_at": "2025-05-25T00:00:00Z",
    }
    fraud_service.repo.save_fraud_pattern.return_value = {}

    request = FraudAnalysisRequest(
        claim_id="claim-456",
        claim_type="motor",
        amount=75000.0,
        description="Total loss vehicle claim",
        user_id="user2",
        policy_number="POL-002",
    )

    result = fraud_service.analyze_claim(request)

    assert result.score == 85
    assert result.risk_level == RiskLevel.HIGH
    fraud_service.repo.save_fraud_pattern.assert_called_once()


def test_get_fraud_score_not_found(fraud_service):
    """Getting a non-existent fraud score should raise 404."""
    fraud_service.repo.get_fraud_score.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        fraud_service.get_fraud_score("nonexistent")
    assert exc_info.value.status_code == 404


def test_get_flagged_claims(fraud_service):
    """Getting flagged claims should return high-risk items."""
    fraud_service.repo.get_flagged_claims.return_value = [
        {
            "claim_id": "claim-789",
            "score": 92,
            "risk_level": "High",
            "explanation": "Suspected fraud.",
            "indicators": ["Pattern match"],
            "analyzed_at": "2025-05-25T00:00:00Z",
            "user_id": "user3",
            "claim_type": "property",
            "amount": "50000",
        }
    ]

    result = fraud_service.get_flagged_claims()

    assert len(result) == 1
    assert result[0].claim_id == "claim-789"
    assert result[0].score == 92
    assert result[0].risk_level == RiskLevel.HIGH
