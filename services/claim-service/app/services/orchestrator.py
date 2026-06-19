"""Service orchestrator — coordinates calls to other microservices."""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ServiceOrchestrator:
    """Orchestrates synchronous REST calls to downstream services."""

    def __init__(self):
        self.http_client = httpx.Client(timeout=30.0)

    def analyze_fraud(self, claim: dict) -> dict:
        """Call Fraud Service to analyze claim for fraud."""
        try:
            response = self.http_client.post(
                f"{settings.fraud_service_url}/api/fraud/analyze",
                json={
                    "claim_id": claim["claim_id"],
                    "claim_type": claim["claim_type"],
                    "amount": float(claim["amount"]),
                    "description": claim["description"],
                    "user_id": claim["user_id"],
                },
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"Fraud service unavailable: {e}")

        # Fallback: return pending status if fraud service is unavailable
        return {"score": 0, "risk_level": "pending", "explanation": "Fraud analysis pending"}

    def evaluate_rules(self, claim: dict, fraud_result: dict) -> dict:
        """Call Rules Service to evaluate claim against assessment rules."""
        try:
            response = self.http_client.post(
                f"{settings.rules_service_url}/api/rules/evaluate",
                json={
                    "claim_id": claim["claim_id"],
                    "claim_type": claim["claim_type"],
                    "amount": float(claim["amount"]),
                    "fraud_score": fraud_result.get("score", 0),
                    "fraud_risk_level": fraud_result.get("risk_level", "unknown"),
                },
            )
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"Rules service unavailable: {e}")

        # Fallback: route to manual review
        return {"decision": "manual_review", "reason": "Rules service unavailable"}

    def get_extracted_data(self, document_ids: list) -> list:
        """Call Document Service to get extracted data for documents."""
        extracted = []
        for doc_id in document_ids:
            try:
                response = self.http_client.get(
                    f"{settings.document_service_url}/api/documents/{doc_id}/extracted",
                )
                if response.status_code == 200:
                    extracted.append(response.json())
            except httpx.RequestError as e:
                logger.warning(f"Document service unavailable for {doc_id}: {e}")
        return extracted

    def send_notification(
        self,
        user_id: str,
        claim_id: str,
        event_type: str,
        status: str,
    ) -> None:
        """Call Notification Service to send status update notification."""
        try:
            self.http_client.post(
                f"{settings.notification_service_url}/api/notifications/send",
                json={
                    "user_id": user_id,
                    "claim_id": claim_id,
                    "event_type": event_type,
                    "status": status,
                },
            )
        except httpx.RequestError as e:
            logger.warning(f"Notification service unavailable: {e}")
            # Non-critical: claim processing continues even if notification fails
