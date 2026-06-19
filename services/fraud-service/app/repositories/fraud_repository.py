"""Fraud repository — DynamoDB operations for fraud-scores and fraud-patterns tables."""

from datetime import datetime, timezone
from typing import Optional

import boto3

from app.config import settings


class FraudRepository:
    """CRUD operations on fraud DynamoDB tables."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.scores_table = self.dynamodb.Table(settings.fraud_scores_table)
        self.patterns_table = self.dynamodb.Table(settings.fraud_patterns_table)

    def save_fraud_score(self, score_data: dict) -> dict:
        """Save fraud analysis result."""
        score_data["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        self.scores_table.put_item(Item=score_data)
        return score_data

    def get_fraud_score(self, claim_id: str) -> Optional[dict]:
        """Get fraud score for a claim."""
        response = self.scores_table.get_item(Key={"claim_id": claim_id})
        return response.get("Item")

    def get_flagged_claims(self) -> list:
        """Get all claims flagged as high risk (score >= threshold)."""
        response = self.scores_table.scan(
            FilterExpression="score >= :threshold",
            ExpressionAttributeValues={":threshold": settings.fraud_threshold},
        )
        return response.get("Items", [])

    def save_fraud_pattern(self, pattern_data: dict) -> dict:
        """Save a fraud pattern for future reference."""
        pattern_data["created_at"] = datetime.now(timezone.utc).isoformat()
        self.patterns_table.put_item(Item=pattern_data)
        return pattern_data

    def get_fraud_patterns(self, claim_type: Optional[str] = None) -> list:
        """Get known fraud patterns, optionally filtered by claim type."""
        if claim_type:
            response = self.patterns_table.query(
                IndexName="claim_type-index",
                KeyConditionExpression="claim_type = :ct",
                ExpressionAttributeValues={":ct": claim_type},
            )
        else:
            response = self.patterns_table.scan()

        return response.get("Items", [])
