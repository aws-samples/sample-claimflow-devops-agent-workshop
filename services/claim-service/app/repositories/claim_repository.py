"""Claim repository — DynamoDB operations for claims and claim-history tables."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import boto3

from app.config import settings


class ClaimRepository:
    """CRUD operations on the claims DynamoDB table."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.claims_table = self.dynamodb.Table(settings.claims_table)
        self.history_table = self.dynamodb.Table(settings.claim_history_table)

    def create_claim(self, claim_data: dict) -> dict:
        """Create a new claim record."""
        claim_data["claim_id"] = str(uuid.uuid4())
        claim_data["reference_number"] = self._generate_reference()
        claim_data["created_at"] = datetime.now(timezone.utc).isoformat()
        claim_data["updated_at"] = claim_data["created_at"]
        claim_data["document_ids"] = claim_data.get("document_ids", [])

        # Convert floats to Decimal for DynamoDB
        claim_data = self._convert_floats(claim_data)

        self.claims_table.put_item(Item=claim_data)
        return claim_data

    def get_claim(self, claim_id: str) -> Optional[dict]:
        """Get claim by ID."""
        response = self.claims_table.get_item(Key={"claim_id": claim_id})
        return response.get("Item")

    def update_claim(self, claim_id: str, updates: dict) -> Optional[dict]:
        """Update claim attributes."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Convert floats to Decimal for DynamoDB
        updates = self._convert_floats(updates)

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
            return self.get_claim(claim_id)

        response = self.claims_table.update_item(
            Key={"claim_id": claim_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def list_claims_by_user(self, user_id: str, status: Optional[str] = None) -> list:
        """List claims for a specific user."""
        kwargs = {
            "IndexName": "user_id-index",
            "KeyConditionExpression": "user_id = :uid",
            "ExpressionAttributeValues": {":uid": user_id},
            "ScanIndexForward": False,
        }
        if status:
            kwargs["FilterExpression"] = "#status = :status"
            kwargs["ExpressionAttributeValues"][":status"] = status
            kwargs["ExpressionAttributeNames"] = {"#status": "status"}

        response = self.claims_table.query(**kwargs)
        return response.get("Items", [])

    def list_claims_by_status(self, status: str) -> list:
        """List claims by status (for adjudicators)."""
        response = self.claims_table.query(
            IndexName="status-index",
            KeyConditionExpression="#status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":status": status},
            ScanIndexForward=False,
        )
        return response.get("Items", [])

    def list_all_claims(self) -> list:
        """List all claims (for adjudicators/admins)."""
        response = self.claims_table.scan()
        items = response.get("Items", [])
        # Sort by created_at descending
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def add_history_entry(
        self,
        claim_id: str,
        previous_status: Optional[str],
        new_status: str,
        changed_by: str,
        notes: Optional[str] = None,
    ) -> dict:
        """Add a status change entry to claim history."""
        entry = {
            "claim_id": claim_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_status": previous_status or "none",
            "new_status": new_status,
            "changed_by": changed_by,
            "notes": notes or "",
        }
        self.history_table.put_item(Item=entry)
        return entry

    def get_claim_history(self, claim_id: str) -> list:
        """Get status change history for a claim."""
        response = self.history_table.query(
            KeyConditionExpression="claim_id = :cid",
            ExpressionAttributeValues={":cid": claim_id},
            ScanIndexForward=True,
        )
        return response.get("Items", [])

    def _generate_reference(self) -> str:
        """Generate a unique claim reference number."""
        now = datetime.now(timezone.utc)
        short_id = uuid.uuid4().hex[:8].upper()
        return f"CLM-{now.strftime('%Y%m%d')}-{short_id}"

    def _convert_floats(self, data: dict) -> dict:
        """Convert float values to Decimal for DynamoDB compatibility."""
        converted = {}
        for key, value in data.items():
            if isinstance(value, float):
                converted[key] = Decimal(str(value))
            elif isinstance(value, dict):
                converted[key] = self._convert_floats(value)
            else:
                converted[key] = value
        return converted
