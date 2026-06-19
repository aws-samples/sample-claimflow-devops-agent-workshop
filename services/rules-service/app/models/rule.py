"""Rules engine data models and schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Decision(str, Enum):
    """Rule evaluation decisions."""

    AUTO_APPROVE = "auto_approve"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"


class RuleEvaluationRequest(BaseModel):
    """Request schema for rule evaluation."""

    claim_id: str = Field(..., min_length=1)
    claim_type: str
    amount: float = Field(..., gt=0)
    fraud_score: int = Field(..., ge=0, le=100)
    fraud_risk_level: str


class RuleEvaluationResponse(BaseModel):
    """Response schema for rule evaluation results."""

    claim_id: str
    decision: Decision
    settlement_amount: Optional[float] = None
    reason: str
    rules_applied: list[str] = []
    evaluated_at: str


class RuleCreate(BaseModel):
    """Request schema for creating a rule."""

    rule_name: str = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: int = Field(default=100, ge=1)
    auto_approve_threshold: Optional[float] = None
    coverage_limit: Optional[float] = None
    fraud_score_threshold: Optional[int] = None
    is_active: bool = True


class RuleUpdate(BaseModel):
    """Request schema for updating a rule."""

    rule_name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    auto_approve_threshold: Optional[float] = None
    coverage_limit: Optional[float] = None
    fraud_score_threshold: Optional[int] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    """Response schema for rule data."""

    rule_id: str
    rule_name: str
    claim_type: str
    description: str
    priority: int
    auto_approve_threshold: Optional[float] = None
    coverage_limit: Optional[float] = None
    fraud_score_threshold: Optional[int] = None
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None
