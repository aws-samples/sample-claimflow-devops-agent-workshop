"""Claim service — core business logic for claim lifecycle management."""

from typing import Optional

from fastapi import HTTPException, status

from app.config import settings
from app.models.claim import (
    ClaimApproval,
    ClaimCreate,
    ClaimRejection,
    ClaimResponse,
    ClaimStatus,
    ClaimUpdate,
    PaginatedClaimList,
)
from app.repositories.claim_repository import ClaimRepository
from app.services.orchestrator import ServiceOrchestrator


class ClaimService:
    """Handles claim lifecycle operations."""

    def __init__(self):
        self.repo = ClaimRepository()
        self.orchestrator = ServiceOrchestrator()

    def create_claim(self, user_id: str, claim_data: ClaimCreate) -> ClaimResponse:
        """Create a new claim in draft status."""
        claim_dict = claim_data.model_dump(exclude_none=True)
        claim_dict["user_id"] = user_id
        claim_dict["status"] = ClaimStatus.DRAFT.value
        claim_dict["claim_type"] = claim_dict["claim_type"].value

        created = self.repo.create_claim(claim_dict)

        self.repo.add_history_entry(
            claim_id=created["claim_id"],
            previous_status=None,
            new_status=ClaimStatus.DRAFT.value,
            changed_by=user_id,
            notes="Claim created",
        )

        return self._to_response(created)

    def submit_claim(self, claim_id: str, user_id: str) -> ClaimResponse:
        """Submit a draft claim — moves to under_review for adjudicator processing."""
        claim = self._get_claim_or_404(claim_id)
        self._verify_ownership(claim, user_id)

        if claim["status"] != ClaimStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft claims can be submitted",
            )

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        # Move directly to under_review (skip fraud/rules for demo)
        updates = {
            "status": ClaimStatus.UNDER_REVIEW.value,
            "submitted_at": now,
        }

        updated = self.repo.update_claim(claim_id, updates)

        self.repo.add_history_entry(
            claim_id=claim_id,
            previous_status=ClaimStatus.DRAFT.value,
            new_status=ClaimStatus.UNDER_REVIEW.value,
            changed_by=user_id,
            notes="Claim submitted for review",
        )

        return self._to_response(updated)

    def get_claim(self, claim_id: str, user_id: str, user_role: str) -> ClaimResponse:
        """Get claim details (owner or adjudicator/admin)."""
        claim = self._get_claim_or_404(claim_id)

        if user_role == "policyholder" and claim["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return self._to_response(claim)

    def list_claims(
        self,
        user_id: str,
        user_role: str,
        claim_status: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedClaimList:
        """List claims — user's own claims or all claims for adjudicator/admin."""
        if user_role == "policyholder":
            items = self.repo.list_claims_by_user(user_id, status=claim_status)
        elif claim_status:
            items = self.repo.list_claims_by_status(claim_status)
        else:
            # For adjudicators/admins, show ALL claims
            items = self.repo.list_all_claims()

        total = len(items)
        start = (page - 1) * size
        end = start + size
        page_items = items[start:end]

        return PaginatedClaimList(
            items=[self._to_response(item) for item in page_items],
            total=total,
            page=page,
            size=size,
        )

    def update_claim(self, claim_id: str, user_id: str, updates: ClaimUpdate) -> ClaimResponse:
        """Update a draft claim."""
        claim = self._get_claim_or_404(claim_id)
        self._verify_ownership(claim, user_id)

        if claim["status"] != ClaimStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft claims can be edited",
            )

        update_dict = updates.model_dump(exclude_none=True)
        if not update_dict:
            return self._to_response(claim)

        updated = self.repo.update_claim(claim_id, update_dict)
        return self._to_response(updated)

    def approve_claim(self, claim_id: str, adjudicator_id: str, approval: ClaimApproval) -> ClaimResponse:
        """Approve a claim (adjudicator only)."""
        claim = self._get_claim_or_404(claim_id)

        if claim["status"] not in [ClaimStatus.UNDER_REVIEW.value, ClaimStatus.ASSESSMENT.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Claim is not in a reviewable state",
            )

        updates = {
            "status": ClaimStatus.APPROVED.value,
            "settlement_amount": approval.settlement_amount,
        }
        updated = self.repo.update_claim(claim_id, updates)

        self.repo.add_history_entry(
            claim_id=claim_id,
            previous_status=claim["status"],
            new_status=ClaimStatus.APPROVED.value,
            changed_by=adjudicator_id,
            notes=approval.notes,
        )

        self.orchestrator.send_notification(
            user_id=claim["user_id"],
            claim_id=claim_id,
            event_type="claim_approved",
            status=ClaimStatus.APPROVED.value,
        )

        return self._to_response(updated)

    def reject_claim(self, claim_id: str, adjudicator_id: str, rejection: ClaimRejection) -> ClaimResponse:
        """Reject a claim (adjudicator only)."""
        claim = self._get_claim_or_404(claim_id)

        if claim["status"] not in [ClaimStatus.UNDER_REVIEW.value, ClaimStatus.ASSESSMENT.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Claim is not in a reviewable state",
            )

        updates = {
            "status": ClaimStatus.REJECTED.value,
            "rejection_reason": rejection.reason,
        }
        updated = self.repo.update_claim(claim_id, updates)

        self.repo.add_history_entry(
            claim_id=claim_id,
            previous_status=claim["status"],
            new_status=ClaimStatus.REJECTED.value,
            changed_by=adjudicator_id,
            notes=rejection.reason,
        )

        self.orchestrator.send_notification(
            user_id=claim["user_id"],
            claim_id=claim_id,
            event_type="claim_rejected",
            status=ClaimStatus.REJECTED.value,
        )

        return self._to_response(updated)

    def settle_claim(self, claim_id: str, adjudicator_id: str) -> ClaimResponse:
        """Move an approved claim to settlement status."""
        claim = self._get_claim_or_404(claim_id)

        if claim["status"] != ClaimStatus.APPROVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only approved claims can be settled",
            )

        updates = {"status": ClaimStatus.SETTLEMENT.value}
        updated = self.repo.update_claim(claim_id, updates)

        self.repo.add_history_entry(
            claim_id=claim_id,
            previous_status=ClaimStatus.APPROVED.value,
            new_status=ClaimStatus.SETTLEMENT.value,
            changed_by=adjudicator_id,
            notes="Settlement initiated",
        )

        return self._to_response(updated)

    def close_claim(self, claim_id: str, adjudicator_id: str) -> ClaimResponse:
        """Close a settled or rejected claim."""
        claim = self._get_claim_or_404(claim_id)

        if claim["status"] not in [ClaimStatus.SETTLEMENT.value, ClaimStatus.REJECTED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only settled or rejected claims can be closed",
            )

        updates = {"status": ClaimStatus.CLOSED.value}
        updated = self.repo.update_claim(claim_id, updates)

        self.repo.add_history_entry(
            claim_id=claim_id,
            previous_status=claim["status"],
            new_status=ClaimStatus.CLOSED.value,
            changed_by=adjudicator_id,
            notes="Claim closed",
        )

        return self._to_response(updated)

    def get_claim_history(self, claim_id: str, user_id: str, user_role: str) -> list:
        """Get claim status change history."""
        claim = self._get_claim_or_404(claim_id)

        if user_role == "policyholder" and claim["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return self.repo.get_claim_history(claim_id)

    def _get_claim_or_404(self, claim_id: str) -> dict:
        """Get claim or raise 404."""
        claim = self.repo.get_claim(claim_id)
        if not claim:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
        return claim

    def _verify_ownership(self, claim: dict, user_id: str) -> None:
        """Verify user owns the claim."""
        if claim["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    def _to_response(self, claim: dict) -> ClaimResponse:
        """Convert DynamoDB item to ClaimResponse."""
        return ClaimResponse(
            claim_id=claim["claim_id"],
            user_id=claim["user_id"],
            claim_type=claim["claim_type"],
            status=claim["status"],
            description=claim["description"],
            amount=float(claim["amount"]),
            policy_number=claim["policy_number"],
            reference_number=claim["reference_number"],
            fraud_score=float(claim["fraud_score"]) if claim.get("fraud_score") else None,
            fraud_risk_level=claim.get("fraud_risk_level"),
            settlement_amount=float(claim["settlement_amount"]) if claim.get("settlement_amount") else None,
            rejection_reason=claim.get("rejection_reason"),
            document_ids=claim.get("document_ids", []),
            created_at=claim["created_at"],
            updated_at=claim.get("updated_at"),
            submitted_at=claim.get("submitted_at"),
            hospital_name=claim.get("hospital_name"),
            diagnosis=claim.get("diagnosis"),
            treatment_dates=claim.get("treatment_dates"),
            vehicle_details=claim.get("vehicle_details"),
            incident_type=claim.get("incident_type"),
            incident_location=claim.get("incident_location"),
            property_address=claim.get("property_address"),
            damage_type=claim.get("damage_type"),
            trip_details=claim.get("trip_details"),
            incident_date=claim.get("incident_date"),
        )
