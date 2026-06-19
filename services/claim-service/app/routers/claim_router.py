"""Claim router — all claim lifecycle endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import get_current_user, require_role
from app.models.claim import (
    ClaimApproval,
    ClaimCreate,
    ClaimRejection,
    ClaimResponse,
    ClaimUpdate,
    PaginatedClaimList,
)
from app.services.claim_service import ClaimService

router = APIRouter()
claim_service = ClaimService()


@router.post("", response_model=ClaimResponse, status_code=201)
async def create_claim(
    claim_data: ClaimCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new claim (draft status)."""
    return claim_service.create_claim(current_user["user_id"], claim_data)


@router.post("/{claim_id}/submit", response_model=ClaimResponse)
async def submit_claim(
    claim_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Submit a draft claim — triggers fraud check and assessment."""
    return claim_service.submit_claim(claim_id, current_user["user_id"])


@router.get("", response_model=PaginatedClaimList)
async def list_claims(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List claims — own claims for policyholders, all for adjudicators/admins."""
    return claim_service.list_claims(
        user_id=current_user["user_id"],
        user_role=current_user["role"],
        claim_status=status,
        page=page,
        size=size,
    )


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get claim details."""
    return claim_service.get_claim(claim_id, current_user["user_id"], current_user["role"])


@router.put("/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    claim_id: str,
    updates: ClaimUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a draft claim."""
    return claim_service.update_claim(claim_id, current_user["user_id"], updates)


@router.post("/{claim_id}/approve", response_model=ClaimResponse)
async def approve_claim(
    claim_id: str,
    approval: ClaimApproval,
    current_user: dict = Depends(require_role("adjudicator", "admin")),
):
    """Approve a claim with settlement amount (adjudicator/admin only)."""
    return claim_service.approve_claim(claim_id, current_user["user_id"], approval)


@router.post("/{claim_id}/reject", response_model=ClaimResponse)
async def reject_claim(
    claim_id: str,
    rejection: ClaimRejection,
    current_user: dict = Depends(require_role("adjudicator", "admin")),
):
    """Reject a claim with reason (adjudicator/admin only)."""
    return claim_service.reject_claim(claim_id, current_user["user_id"], rejection)


@router.post("/{claim_id}/settle", response_model=ClaimResponse)
async def settle_claim(
    claim_id: str,
    current_user: dict = Depends(require_role("adjudicator", "admin")),
):
    """Move an approved claim to settlement (adjudicator/admin only)."""
    return claim_service.settle_claim(claim_id, current_user["user_id"])


@router.post("/{claim_id}/close", response_model=ClaimResponse)
async def close_claim(
    claim_id: str,
    current_user: dict = Depends(require_role("adjudicator", "admin")),
):
    """Close a settled or rejected claim (adjudicator/admin only)."""
    return claim_service.close_claim(claim_id, current_user["user_id"])


@router.get("/{claim_id}/history")
async def get_claim_history(
    claim_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get claim status change history."""
    return claim_service.get_claim_history(claim_id, current_user["user_id"], current_user["role"])


@router.post("/simulate/lifecycle", response_model=ClaimResponse)
async def simulate_lifecycle(
    current_user: dict = Depends(require_role("admin")),
):
    """Simulate a complete claim lifecycle (admin only). Creates, submits, approves, settles, and closes a claim."""
    import secrets
    from decimal import Decimal

    # Random claim data. Uses the secrets module (not the random module) to
    # satisfy security linters; this only generates demonstration claim data.
    claim_types = ["health", "motor", "property", "travel"]
    descriptions = {
        "health": "Simulated health claim - hospitalization for treatment at City Hospital",
        "motor": "Simulated motor claim - vehicle damage from road accident on highway",
        "property": "Simulated property claim - water damage from pipe burst in apartment",
        "travel": "Simulated travel claim - flight cancellation and hotel rebooking costs",
    }
    ct = secrets.choice(claim_types)
    amount = 10000 + secrets.randbelow(490001)

    # Step 1: Create
    claim_data = {
        "claim_type": ct,
        "amount": Decimal(str(amount)),
        "description": descriptions[ct],
        "policy_number": f"POL-SIM-{1000 + secrets.randbelow(9000)}",
        "user_id": current_user["user_id"],
        "status": "draft",
    }
    created = claim_service.repo.create_claim(claim_data)
    claim_id = created["claim_id"]
    claim_service.repo.add_history_entry(claim_id, None, "draft", "simulator", "Simulated claim created")

    # Step 2: Submit (move to under_review)
    from datetime import datetime, timezone
    claim_service.repo.update_claim(claim_id, {"status": "under_review", "submitted_at": datetime.now(timezone.utc).isoformat()})
    claim_service.repo.add_history_entry(claim_id, "draft", "under_review", "simulator", "Auto-submitted")

    # Step 3: Approve or Reject (70/30)
    if secrets.randbelow(100) < 70:
        settlement = Decimal(str(round(amount * (0.85 + secrets.randbelow(11) / 100.0))))
        claim_service.repo.update_claim(claim_id, {"status": "approved", "settlement_amount": settlement})
        claim_service.repo.add_history_entry(claim_id, "under_review", "approved", "simulator", f"Auto-approved, settlement: {settlement}")

        # Step 4: Settle
        claim_service.repo.update_claim(claim_id, {"status": "settlement"})
        claim_service.repo.add_history_entry(claim_id, "approved", "settlement", "simulator", "Settlement initiated")

        # Step 5: Close
        claim_service.repo.update_claim(claim_id, {"status": "closed"})
        claim_service.repo.add_history_entry(claim_id, "settlement", "closed", "simulator", "Claim closed")
    else:
        claim_service.repo.update_claim(claim_id, {"status": "rejected", "rejection_reason": "Simulated rejection - policy criteria not met"})
        claim_service.repo.add_history_entry(claim_id, "under_review", "rejected", "simulator", "Auto-rejected")

        # Close rejected
        claim_service.repo.update_claim(claim_id, {"status": "closed"})
        claim_service.repo.add_history_entry(claim_id, "rejected", "closed", "simulator", "Claim closed")

    # Return final state
    final = claim_service.repo.get_claim(claim_id)
    return claim_service._to_response(final)
