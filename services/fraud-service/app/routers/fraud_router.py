"""Fraud router — fraud analysis endpoints."""

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import get_current_user, require_role
from app.models.fraud import FlaggedClaimResponse, FraudAnalysisRequest, FraudAnalysisResponse
from app.services.fraud_service import FraudService

router = APIRouter()
fraud_service = FraudService()


@router.post("/analyze", response_model=FraudAnalysisResponse)
async def analyze_claim(
    request: FraudAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """Analyze a claim for potential fraud using AI."""
    return fraud_service.analyze_claim(request)


@router.get("/scores/{claim_id}", response_model=FraudAnalysisResponse)
async def get_fraud_score(
    claim_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get the fraud analysis score for a specific claim."""
    return fraud_service.get_fraud_score(claim_id)


@router.get("/flagged", response_model=list[FlaggedClaimResponse])
async def get_flagged_claims(
    current_user: dict = Depends(require_role("adjudicator", "admin")),
):
    """Get all claims flagged as high risk (adjudicator/admin only)."""
    return fraud_service.get_flagged_claims()
