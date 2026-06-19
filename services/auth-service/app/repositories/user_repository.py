"""User repository — DynamoDB operations for users table."""

from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings


class UserRepository:
    """CRUD operations on the users DynamoDB table."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.table = self.dynamodb.Table(settings.users_table)

    def create_user(self, user_data: dict) -> dict:
        """Create a new user record."""
        user_data["created_at"] = datetime.now(timezone.utc).isoformat()
        user_data["status"] = "active"
        user_data["last_login"] = None

        try:
            self.table.put_item(
                Item=user_data,
                ConditionExpression="attribute_not_exists(user_id)",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError("User ID already exists")
            raise

        return user_data

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by user_id."""
        response = self.table.get_item(Key={"user_id": user_id})
        return response.get("Item")

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email using GSI."""
        response = self.table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :email",
            ExpressionAttributeValues={":email": email},
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def update_user(self, user_id: str, updates: dict) -> Optional[dict]:
        """Update user attributes."""
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
            return self.get_user_by_id(user_id)

        response = self.table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def update_last_login(self, user_id: str) -> None:
        """Update last login timestamp."""
        self.table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET last_login = :ts",
            ExpressionAttributeValues={":ts": datetime.now(timezone.utc).isoformat()},
        )

    def list_users(self, role: Optional[str] = None, status: Optional[str] = None) -> list:
        """List users with optional filtering."""
        scan_kwargs = {}
        filter_parts = []
        expr_values = {}

        if role:
            filter_parts.append("#role = :role")
            expr_values[":role"] = role
        if status:
            filter_parts.append("#status = :status")
            expr_values[":status"] = status

        if filter_parts:
            scan_kwargs["FilterExpression"] = " AND ".join(filter_parts)
            scan_kwargs["ExpressionAttributeValues"] = expr_values
            scan_kwargs["ExpressionAttributeNames"] = {"#role": "role", "#status": "status"}

        response = self.table.scan(**scan_kwargs)
        return response.get("Items", [])

    def deactivate_user(self, user_id: str) -> Optional[dict]:
        """Set user status to inactive."""
        return self.update_user(user_id, {"status": "inactive"})
