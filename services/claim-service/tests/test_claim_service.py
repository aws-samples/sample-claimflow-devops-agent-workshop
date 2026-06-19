"""Tests for claim service business logic."""

import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from app.models.claim import ClaimCreate, ClaimType, ClaimApproval, ClaimRejection
from app.services.claim_service import ClaimService


@pytest.fixture
def claim_service():
    """Create ClaimService with mocked dependencies."""
    with patch("app.services.claim_service.ClaimRepository") as mock_repo, \
         patch("app.services.claim_service.ServiceOrchestrator") as mock_orch:
        service = ClaimService()
        service.repo = mock_repo.return_value
        service.orchestrator = mock_orch.return_value
        yield service


def test_create_claim_success(claim_service):
    """Creating a claim should return draft status."""
    claim_service.repo.create_claim.return_value = {
        "claim_id": "test-123",
        "user_id": "user1",
        "claim_type": "health",
        "status": "draft",
        "description": "Hospital visit for treatment",
        "amount": 5000.0,
        "policy_number": "POL-001",
        "reference_number": "CLM-20250525-ABCD1234",
        "created_at": "2025-05-25T00:00:00Z",
        "document_ids": [],
    }
    claim_service.repo.add_history_entry.return_value = {}

    claim_data = ClaimCreate(
        claim_type=ClaimType.HEALTH,
        description="Hospital visit for treatment",
        amount=5000.0,
        policy_number="POL-001",
    )

    result = claim_service.create_claim("user1", claim_data)
    assert result.claim_id == "test-123"
    assert result.status == "draft"
    assert result.claim_type == "health"


def test_submit_claim_not_draft(claim_service):
    """Submitting a non-draft claim should raise 400."""
    claim_service.repo.get_claim.return_value = {
        "claim_id": "test-123",
        "user_id": "user1",
        "status": "submitted",
    }

    with pytest.raises(HTTPException) as exc_info:
        claim_service.submit_claim("test-123", "user1")
    assert exc_info.value.status_code == 400


def test_submit_claim_wrong_user(claim_service):
    """Submitting another user's claim should raise 403."""
    claim_service.repo.get_claim.return_value = {
        "claim_id": "test-123",
        "user_id": "user1",
        "status": "draft",
    }

    with pytest.raises(HTTPException) as exc_info:
        claim_service.submit_claim("test-123", "user2")
    assert exc_info.value.status_code == 403


def test_approve_claim_success(claim_service):
    """Approving a claim under review should succeed."""
    claim_service.repo.get_claim.return_value = {
        "claim_id": "test-123",
        "user_id": "user1",
        "status": "under_review",
    }
    claim_service.repo.update_claim.return_value = {
        "claim_id": "test-123",
        "user_id": "user1",
        "claim_type": "health",
        "status": "approved",
        "description": "Test claim",
        "amount": 5000.0,
        "policy_number": "POL-001",
        "reference_number": "CLM-20250525-ABCD1234",
        "settlement_amount": 4500.0,
        "created_at": "2025-05-25T00:00:00Z",
        "document_ids": [],
    }
    claim_service.repo.add_history_entry.return_value = {}
    claim_service.orchestrator.send_notification.return_value = None

    approval = ClaimApproval(settlement_amount=4500.0, notes="Approved after review")
    result = claim_service.approve_claim("test-123", "adjudicator1", approval)

    assert result.status == "approved"
    assert result.settlement_amount == 4500.0


def test_reject_claim_not_reviewable(claim_service):
    """Rejecting a claim not under review should raise 400."""
    claim_service.repo.get_claim.return_value = {
        "claim_id": "test-123",
        "user_id": "user1",
        "status": "draft",
    }

    rejection = ClaimRejection(reason="Insufficient documentation provided")

    with pytest.raises(HTTPException) as exc_info:
        claim_service.reject_claim("test-123", "adjudicator1", rejection)
    assert exc_info.value.status_code == 400


def test_get_claim_not_found(claim_service):
    """Getting a non-existent claim should raise 404."""
    claim_service.repo.get_claim.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        claim_service.get_claim("nonexistent", "user1", "policyholder")
    assert exc_info.value.status_code == 404
