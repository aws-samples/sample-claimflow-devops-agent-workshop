"""Evaluation engine — evaluates claims against rules."""

import logging
import uuid
from typing import Optional

from app.models.rule import Decision, RuleEvaluationRequest, RuleEvaluationResponse
from app.repositories.rules_repository import RulesRepository

logger = logging.getLogger(__name__)

# Default thresholds (used when no specific rules are configured)
DEFAULT_FRAUD_THRESHOLD = 70
DEFAULT_AUTO_APPROVE_THRESHOLD = 5000.0
DEFAULT_COVERAGE_LIMIT = 100000.0
LOW_FRAUD_THRESHOLD = 30


class EvaluationEngine:
    """Evaluates claims against configured rules."""

    def __init__(self):
        self.repo = RulesRepository()

    def evaluate(self, request: RuleEvaluationRequest) -> RuleEvaluationResponse:
        """Evaluate a claim against all applicable rules.

        Decision logic:
        1. If fraud_score >= 70 → manual_review
        2. If amount > coverage_limit → reject
        3. If fraud_score < 30 AND amount < auto_approve_threshold → auto_approve
           (settlement_amount = amount * 0.9)
        4. Otherwise → manual_review
        """
        rules_applied = []

        # Get applicable rules for this claim type
        rules = self.repo.list_rules_by_claim_type(request.claim_type)
        active_rules = [r for r in rules if r.get("is_active", True)]

        # Determine thresholds from rules or use defaults
        fraud_threshold = DEFAULT_FRAUD_THRESHOLD
        auto_approve_threshold = DEFAULT_AUTO_APPROVE_THRESHOLD
        coverage_limit = DEFAULT_COVERAGE_LIMIT

        for rule in active_rules:
            if rule.get("fraud_score_threshold"):
                fraud_threshold = int(rule["fraud_score_threshold"])
            if rule.get("auto_approve_threshold"):
                auto_approve_threshold = float(rule["auto_approve_threshold"])
            if rule.get("coverage_limit"):
                coverage_limit = float(rule["coverage_limit"])

        # Rule 1: High fraud score → manual review
        if request.fraud_score >= fraud_threshold:
            decision = Decision.MANUAL_REVIEW
            reason = f"Fraud score ({request.fraud_score}) exceeds threshold ({fraud_threshold}). Manual review required."
            rules_applied.append("fraud_score_check")
            settlement_amount = None

        # Rule 2: Amount exceeds coverage limit → reject
        elif request.amount > coverage_limit:
            decision = Decision.REJECT
            reason = f"Claim amount (${request.amount:,.2f}) exceeds coverage limit (${coverage_limit:,.2f})."
            rules_applied.append("coverage_limit_check")
            settlement_amount = None

        # Rule 3: Low fraud + low amount → auto approve
        elif request.fraud_score < LOW_FRAUD_THRESHOLD and request.amount < auto_approve_threshold:
            decision = Decision.AUTO_APPROVE
            settlement_amount = round(request.amount * 0.9, 2)
            reason = f"Low risk claim auto-approved. Settlement: ${settlement_amount:,.2f} (90% of claimed amount)."
            rules_applied.append("auto_approve_check")

        # Rule 4: Everything else → manual review
        else:
            decision = Decision.MANUAL_REVIEW
            reason = "Claim requires manual review based on risk assessment."
            rules_applied.append("default_manual_review")
            settlement_amount = None

        # Save evaluation result
        result_data = {
            "claim_id": request.claim_id,
            "evaluation_id": str(uuid.uuid4()),
            "decision": decision.value,
            "settlement_amount": str(settlement_amount) if settlement_amount else None,
            "reason": reason,
            "rules_applied": rules_applied,
            "fraud_score": request.fraud_score,
            "amount": str(request.amount),
            "claim_type": request.claim_type,
        }

        saved = self.repo.save_evaluation_result(result_data)

        return RuleEvaluationResponse(
            claim_id=request.claim_id,
            decision=decision,
            settlement_amount=settlement_amount,
            reason=reason,
            rules_applied=rules_applied,
            evaluated_at=saved["evaluated_at"],
        )
