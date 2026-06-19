"""Session repository — DynamoDB operations for sessions table."""

import uuid
from datetime import datetime, timezone

import boto3

from app.config import settings


class SessionRepository:
    """Session management on the sessions DynamoDB table."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.table = self.dynamodb.Table(settings.sessions_table)

    def create_session(self, user_id: str, refresh_token: str) -> dict:
        """Create a new session record."""
        session = {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "refresh_token": refresh_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
        self.table.put_item(Item=session)
        return session

    def get_session_by_token(self, user_id: str, refresh_token: str) -> dict | None:
        """Find active session by user_id and refresh token."""
        response = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression="user_id = :uid",
            FilterExpression="refresh_token = :token AND is_active = :active",
            ExpressionAttributeValues={
                ":uid": user_id,
                ":token": refresh_token,
                ":active": True,
            },
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def invalidate_session(self, session_id: str) -> None:
        """Mark a session as inactive."""
        self.table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET is_active = :inactive",
            ExpressionAttributeValues={":inactive": False},
        )

    def invalidate_all_user_sessions(self, user_id: str) -> None:
        """Invalidate all sessions for a user."""
        response = self.table.query(
            IndexName="user_id-index",
            KeyConditionExpression="user_id = :uid",
            FilterExpression="is_active = :active",
            ExpressionAttributeValues={":uid": user_id, ":active": True},
        )
        for item in response.get("Items", []):
            self.invalidate_session(item["session_id"])
