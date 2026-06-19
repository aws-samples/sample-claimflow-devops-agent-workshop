"""Rules router — rule management and evaluation endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.middleware.auth_middleware import get_current_user, require_role
from app.models.rule import (
    RuleCreate,
    RuleEvaluationRequest,
    RuleEvaluationResponse,
    RuleResponse,
    RuleUpdate,
)
from app.services.evaluation_engine import EvaluationEngine
from app.services.rules_service import RulesService

router = APIRouter()
rules_service = RulesService()
evaluation_engine = EvaluationEngine()


@router.post("/evaluate", response_model=RuleEvaluationResponse)
async def evaluate_claim(
    request: RuleEvaluationRequest,
    current_user: dict = Depends(get_current_user),
):
    """Evaluate a claim against all applicable rules."""
    return evaluation_engine.evaluate(request)


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    claim_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List rules, optionally filtered by claim type."""
    return rules_service.get_rules(claim_type)


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    rule_data: RuleCreate,
    current_user: dict = Depends(require_role("admin")),
):
    """Create a new rule (admin only)."""
    return rules_service.create_rule(rule_data)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    updates: RuleUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    """Update an existing rule (admin only)."""
    return rules_service.update_rule(rule_id, updates)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    """Delete a rule (admin only)."""
    rules_service.delete_rule(rule_id)


@router.get("/evaluations/{claim_id}")
async def get_evaluations(
    claim_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get all rule evaluation results for a claim."""
    return rules_service.get_evaluations(claim_id)
