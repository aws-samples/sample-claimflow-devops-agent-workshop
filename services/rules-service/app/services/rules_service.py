"""Rules service — CRUD operations for rules."""

import logging
from typing import Optional

from fastapi import HTTPException, status

from app.models.rule import RuleCreate, RuleResponse, RuleUpdate
from app.repositories.rules_repository import RulesRepository

logger = logging.getLogger(__name__)


class RulesService:
    """Handles CRUD operations for rules."""

    def __init__(self):
        self.repo = RulesRepository()

    def create_rule(self, rule_data: RuleCreate) -> RuleResponse:
        """Create a new rule."""
        rule_dict = rule_data.model_dump(exclude_none=True)
        created = self.repo.create_rule(rule_dict)
        return self._to_response(created)

    def get_rules(self, claim_type: Optional[str] = None) -> list[RuleResponse]:
        """List rules, optionally filtered by claim type."""
        rules = self.repo.list_rules_by_claim_type(claim_type)
        return [self._to_response(r) for r in rules]

    def update_rule(self, rule_id: str, updates: RuleUpdate) -> RuleResponse:
        """Update an existing rule."""
        existing = self.repo.get_rule(rule_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found",
            )

        update_dict = updates.model_dump(exclude_none=True)
        if not update_dict:
            return self._to_response(existing)

        updated = self.repo.update_rule(rule_id, update_dict)
        return self._to_response(updated)

    def delete_rule(self, rule_id: str) -> None:
        """Delete a rule."""
        existing = self.repo.get_rule(rule_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found",
            )
        self.repo.delete_rule(rule_id)

    def get_evaluations(self, claim_id: str) -> list:
        """Get evaluation results for a claim."""
        return self.repo.get_evaluations_by_claim(claim_id)

    def _to_response(self, rule: dict) -> RuleResponse:
        """Convert DynamoDB item to RuleResponse."""
        return RuleResponse(
            rule_id=rule["rule_id"],
            rule_name=rule["rule_name"],
            claim_type=rule["claim_type"],
            description=rule["description"],
            priority=int(rule.get("priority", 100)),
            auto_approve_threshold=float(rule["auto_approve_threshold"]) if rule.get("auto_approve_threshold") else None,
            coverage_limit=float(rule["coverage_limit"]) if rule.get("coverage_limit") else None,
            fraud_score_threshold=int(rule["fraud_score_threshold"]) if rule.get("fraud_score_threshold") else None,
            is_active=rule.get("is_active", True),
            created_at=rule["created_at"],
            updated_at=rule.get("updated_at"),
        )
