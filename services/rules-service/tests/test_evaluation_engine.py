"""Tests for rules evaluation engine."""

import pytest
from unittest.mock import patch, MagicMock

from app.models.rule import Decision, RuleEvaluationRequest
from app.services.evaluation_engine import EvaluationEngine


@pytest.fixture
def evaluation_engine():
    """Create EvaluationEngine with mocked dependencies."""
    with patch("app.services.evaluation_engine.RulesRepository") as mock_repo:
        engine = EvaluationEngine()
        engine.repo = mock_repo.return_value
        yield engine


def test_high_fraud_score_triggers_manual_review(evaluation_engine):
    """Claims with fraud score >= 70 should require manual review."""
    evaluation_engine.repo.list_rules_by_claim_type.return_value = []
    evaluation_engine.repo.save_evaluation_result.return_value = {
        "evaluated_at": "2025-05-25T00:00:00Z"
    }

    request = RuleEvaluationRequest(
        claim_id="claim-123",
        claim_type="health",
        amount=5000.0,
        fraud_score=75,
        fraud_risk_level="High",
    )

    result = evaluation_engine.evaluate(request)

    assert result.decision == Decision.MANUAL_REVIEW
    assert "fraud_score_check" in result.rules_applied
    assert result.settlement_amount is None


def test_amount_exceeds_coverage_limit_rejects(evaluation_engine):
    """Claims exceeding coverage limit should be rejected."""
    evaluation_engine.repo.list_rules_by_claim_type.return_value = [
        {
            "rule_id": "rule-1",
            "is_active": True,
            "coverage_limit": "50000",
        }
    ]
    evaluation_engine.repo.save_evaluation_result.return_value = {
        "evaluated_at": "2025-05-25T00:00:00Z"
    }

    request = RuleEvaluationRequest(
        claim_id="claim-456",
        claim_type="motor",
        amount=75000.0,
        fraud_score=20,
        fraud_risk_level="Low",
    )

    result = evaluation_engine.evaluate(request)

    assert result.decision == Decision.REJECT
    assert "coverage_limit_check" in result.rules_applied


def test_low_risk_auto_approves(evaluation_engine):
    """Low fraud score + low amount should auto-approve at 90%."""
    evaluation_engine.repo.list_rules_by_claim_type.return_value = []
    evaluation_engine.repo.save_evaluation_result.return_value = {
        "evaluated_at": "2025-05-25T00:00:00Z"
    }

    request = RuleEvaluationRequest(
        claim_id="claim-789",
        claim_type="health",
        amount=2000.0,
        fraud_score=10,
        fraud_risk_level="Low",
    )

    result = evaluation_engine.evaluate(request)

    assert result.decision == Decision.AUTO_APPROVE
    assert result.settlement_amount == 1800.0  # 2000 * 0.9
    assert "auto_approve_check" in result.rules_applied


def test_medium_risk_triggers_manual_review(evaluation_engine):
    """Medium fraud score with moderate amount should trigger manual review."""
    evaluation_engine.repo.list_rules_by_claim_type.return_value = []
    evaluation_engine.repo.save_evaluation_result.return_value = {
        "evaluated_at": "2025-05-25T00:00:00Z"
    }

    request = RuleEvaluationRequest(
        claim_id="claim-101",
        claim_type="property",
        amount=8000.0,
        fraud_score=45,
        fraud_risk_level="Medium",
    )

    result = evaluation_engine.evaluate(request)

    assert result.decision == Decision.MANUAL_REVIEW
    assert "default_manual_review" in result.rules_applied
    assert result.settlement_amount is None
