"""Fraud detection data models and schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Fraud risk levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class FraudAnalysisRequest(BaseModel):
    """Request schema for fraud analysis."""

    claim_id: str = Field(..., min_length=1)
    claim_type: str
    amount: float = Field(..., gt=0)
    description: str
    user_id: str
    policy_number: str
    incident_date: Optional[str] = None
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    vehicle_details: Optional[str] = None
    incident_location: Optional[str] = None


class FraudAnalysisResponse(BaseModel):
    """Response schema for fraud analysis results."""

    claim_id: str
    score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    explanation: str
    indicators: list[str] = []
    analyzed_at: str


class FlaggedClaimResponse(BaseModel):
    """Response schema for flagged claims."""

    claim_id: str
    score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    explanation: str
    indicators: list[str] = []
    analyzed_at: str
    user_id: str
    claim_type: str
    amount: float
