"""Claim data models and schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    """Supported claim types."""

    HEALTH = "health"
    MOTOR = "motor"
    PROPERTY = "property"
    TRAVEL = "travel"


class ClaimStatus(str, Enum):
    """Claim lifecycle states."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ASSESSMENT = "assessment"
    APPROVED = "approved"
    REJECTED = "rejected"
    SETTLEMENT = "settlement"
    CLOSED = "closed"


class ClaimCreate(BaseModel):
    """Request schema for creating a claim."""

    claim_type: ClaimType
    description: str = Field(..., min_length=10, max_length=5000)
    amount: float = Field(..., gt=0)
    policy_number: str = Field(..., min_length=1)

    # Type-specific fields (optional, varies by claim type)
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_dates: Optional[str] = None
    vehicle_details: Optional[str] = None
    incident_type: Optional[str] = None
    incident_location: Optional[str] = None
    property_address: Optional[str] = None
    damage_type: Optional[str] = None
    trip_details: Optional[str] = None
    incident_date: Optional[str] = None


class ClaimUpdate(BaseModel):
    """Request schema for updating a draft claim."""

    description: Optional[str] = None
    amount: Optional[float] = None
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_dates: Optional[str] = None
    vehicle_details: Optional[str] = None
    incident_type: Optional[str] = None
    incident_location: Optional[str] = None
    property_address: Optional[str] = None
    damage_type: Optional[str] = None
    trip_details: Optional[str] = None
    incident_date: Optional[str] = None


class ClaimApproval(BaseModel):
    """Request schema for approving a claim."""

    settlement_amount: float = Field(..., gt=0)
    notes: Optional[str] = None


class ClaimRejection(BaseModel):
    """Request schema for rejecting a claim."""

    reason: str = Field(..., min_length=10)


class ClaimResponse(BaseModel):
    """Response schema for claim data."""

    claim_id: str
    user_id: str
    claim_type: str
    status: str
    description: str
    amount: float
    policy_number: str
    reference_number: str
    fraud_score: Optional[float] = None
    fraud_risk_level: Optional[str] = None
    settlement_amount: Optional[float] = None
    rejection_reason: Optional[str] = None
    document_ids: list[str] = []
    created_at: str
    updated_at: Optional[str] = None
    submitted_at: Optional[str] = None

    # Type-specific fields
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_dates: Optional[str] = None
    vehicle_details: Optional[str] = None
    incident_type: Optional[str] = None
    incident_location: Optional[str] = None
    property_address: Optional[str] = None
    damage_type: Optional[str] = None
    trip_details: Optional[str] = None
    incident_date: Optional[str] = None


class ClaimHistoryEntry(BaseModel):
    """A single claim status change entry."""

    claim_id: str
    timestamp: str
    previous_status: Optional[str] = None
    new_status: str
    changed_by: str
    notes: Optional[str] = None


class PaginatedClaimList(BaseModel):
    """Paginated list of claims."""

    items: list[ClaimResponse]
    total: int
    page: int
    size: int
