"""Fraud service — orchestrates fraud analysis."""

import logging

from fastapi import HTTPException, status

from app.config import settings
from app.models.fraud import (
    FlaggedClaimResponse,
    FraudAnalysisRequest,
    FraudAnalysisResponse,
    RiskLevel,
)
from app.repositories.fraud_repository import FraudRepository
from app.services.bedrock_client import BedrockClient

logger = logging.getLogger(__name__)


class FraudService:
    """Handles fraud analysis orchestration."""

    def __init__(self):
        self.repo = FraudRepository()
        self.bedrock = BedrockClient()

    def analyze_claim(self, request: FraudAnalysisRequest) -> FraudAnalysisResponse:
        """Analyze a claim for fraud using AI."""
        claim_data = request.model_dump(exclude_none=True)

        # Run AI analysis
        analysis_result = self.bedrock.analyze_claim_for_fraud(claim_data)

        # Save the score
        score_data = {
            "claim_id": request.claim_id,
            "user_id": request.user_id,
            "claim_type": request.claim_type,
            "amount": str(request.amount),
            "score": analysis_result["score"],
            "risk_level": analysis_result["risk_level"],
            "explanation": analysis_result["explanation"],
            "indicators": analysis_result["indicators"],
        }

        saved = self.repo.save_fraud_score(score_data)

        # If high risk, save pattern for future reference
        if analysis_result["score"] >= settings.fraud_threshold:
            self._save_pattern(request, analysis_result)

        return FraudAnalysisResponse(
            claim_id=request.claim_id,
            score=analysis_result["score"],
            risk_level=RiskLevel(analysis_result["risk_level"]),
            explanation=analysis_result["explanation"],
            indicators=analysis_result["indicators"],
            analyzed_at=saved["analyzed_at"],
        )

    def get_fraud_score(self, claim_id: str) -> FraudAnalysisResponse:
        """Get the fraud score for a specific claim."""
        score = self.repo.get_fraud_score(claim_id)
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fraud score not found for this claim",
            )

        return FraudAnalysisResponse(
            claim_id=score["claim_id"],
            score=int(score["score"]),
            risk_level=RiskLevel(score["risk_level"]),
            explanation=score["explanation"],
            indicators=score.get("indicators", []),
            analyzed_at=score["analyzed_at"],
        )

    def get_flagged_claims(self) -> list[FlaggedClaimResponse]:
        """Get all claims flagged as high risk."""
        flagged = self.repo.get_flagged_claims()

        return [
            FlaggedClaimResponse(
                claim_id=item["claim_id"],
                score=int(item["score"]),
                risk_level=RiskLevel(item["risk_level"]),
                explanation=item["explanation"],
                indicators=item.get("indicators", []),
                analyzed_at=item["analyzed_at"],
                user_id=item["user_id"],
                claim_type=item["claim_type"],
                amount=float(item["amount"]),
            )
            for item in flagged
        ]

    def _save_pattern(self, request: FraudAnalysisRequest, analysis: dict) -> None:
        """Save a fraud pattern for future reference."""
        try:
            pattern_data = {
                "pattern_id": f"pattern-{request.claim_id}",
                "claim_type": request.claim_type,
                "claim_id": request.claim_id,
                "indicators": analysis["indicators"],
                "score": analysis["score"],
                "amount_range": self._get_amount_range(request.amount),
            }
            self.repo.save_fraud_pattern(pattern_data)
        except Exception as e:
            logger.warning(f"Failed to save fraud pattern: {e}")

    def _get_amount_range(self, amount: float) -> str:
        """Categorize amount into a range."""
        if amount < 1000:
            return "low"
        elif amount < 10000:
            return "medium"
        elif amount < 50000:
            return "high"
        else:
            return "very_high"
