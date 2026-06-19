"""Notification repository — DynamoDB operations for notification-log and notification-preferences tables."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3

from app.config import settings


class NotificationRepository:
    """CRUD operations on notification DynamoDB tables."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.log_table = self.dynamodb.Table(settings.notification_log_table)
        self.preferences_table = self.dynamodb.Table(settings.notification_preferences_table)

    def save_notification_log(self, log_data: dict) -> dict:
        """Save a notification log entry."""
        log_data["notification_id"] = str(uuid.uuid4())
        log_data["sent_at"] = datetime.now(timezone.utc).isoformat()
        self.log_table.put_item(Item=log_data)
        return log_data

    def get_notification_logs(
        self,
        user_id: Optional[str] = None,
        claim_id: Optional[str] = None,
    ) -> list:
        """Get notification logs filtered by user_id and/or claim_id."""
        if user_id and claim_id:
            response = self.log_table.query(
                IndexName="user_id-index",
                KeyConditionExpression="user_id = :uid",
                FilterExpression="claim_id = :cid",
                ExpressionAttributeValues={":uid": user_id, ":cid": claim_id},
            )
        elif user_id:
            response = self.log_table.query(
                IndexName="user_id-index",
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
            )
        elif claim_id:
            response = self.log_table.query(
                IndexName="claim_id-index",
                KeyConditionExpression="claim_id = :cid",
                ExpressionAttributeValues={":cid": claim_id},
            )
        else:
            response = self.log_table.scan()

        return response.get("Items", [])

    def get_preferences(self, user_id: str) -> Optional[dict]:
        """Get notification preferences for a user."""
        response = self.preferences_table.get_item(Key={"user_id": user_id})
        return response.get("Item")

    def save_preferences(self, preferences_data: dict) -> dict:
        """Save or update notification preferences."""
        preferences_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.preferences_table.put_item(Item=preferences_data)
        return preferences_data

    def update_preferences(self, user_id: str, updates: dict) -> Optional[dict]:
        """Update notification preferences."""
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
            return self.get_preferences(user_id)

        response = self.preferences_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")
