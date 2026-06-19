"""Rules repository — DynamoDB operations for rules and rule-results tables."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3

from app.config import settings


class RulesRepository:
    """CRUD operations on rules DynamoDB tables."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.rules_table = self.dynamodb.Table(settings.rules_table)
        self.results_table = self.dynamodb.Table(settings.rule_results_table)

    def create_rule(self, rule_data: dict) -> dict:
        """Create a new rule."""
        rule_data["rule_id"] = str(uuid.uuid4())
        rule_data["created_at"] = datetime.now(timezone.utc).isoformat()
        rule_data["updated_at"] = rule_data["created_at"]

        self.rules_table.put_item(Item=rule_data)
        return rule_data

    def get_rule(self, rule_id: str) -> Optional[dict]:
        """Get a rule by ID."""
        response = self.rules_table.get_item(Key={"rule_id": rule_id})
        return response.get("Item")

    def update_rule(self, rule_id: str, updates: dict) -> Optional[dict]:
        """Update rule attributes."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        update_expr_parts = []
        expr_attr_values = {}
        expr_attr_names = {}

        for key, value in updates.items():
            if value is not None:
                safe_key = f"#{key}"
                expr_attr_names[safe_key] = key
                update_expr_parts.append(f"{safe_key} = :{key}")
                expr_attr_values[f":{key}"] = value

        if not update_expr_parts:
            return self.get_rule(rule_id)

        response = self.rules_table.update_item(
            Key={"rule_id": rule_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def delete_rule(self, rule_id: str) -> None:
        """Delete a rule."""
        self.rules_table.delete_item(Key={"rule_id": rule_id})

    def list_rules_by_claim_type(self, claim_type: Optional[str] = None) -> list:
        """List rules, optionally filtered by claim type."""
        if claim_type:
            response = self.rules_table.query(
                IndexName="claim_type-index",
                KeyConditionExpression="claim_type = :ct",
                ExpressionAttributeValues={":ct": claim_type},
            )
        else:
            response = self.rules_table.scan()

        return response.get("Items", [])

    def save_evaluation_result(self, result_data: dict) -> dict:
        """Save a rule evaluation result."""
        result_data["evaluated_at"] = datetime.now(timezone.utc).isoformat()
        self.results_table.put_item(Item=result_data)
        return result_data

    def get_evaluations_by_claim(self, claim_id: str) -> list:
        """Get all evaluation results for a claim."""
        response = self.results_table.query(
            KeyConditionExpression="claim_id = :cid",
            ExpressionAttributeValues={":cid": claim_id},
            ScanIndexForward=False,
        )
        return response.get("Items", [])
