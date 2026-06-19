"""Document repository — DynamoDB operations for document-metadata and extracted-data tables."""

import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3

from app.config import settings


class DocumentRepository:
    """CRUD operations on document DynamoDB tables."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.metadata_table = self.dynamodb.Table(settings.document_metadata_table)
        self.extracted_table = self.dynamodb.Table(settings.extracted_data_table)

    def create_document(self, document_data: dict) -> dict:
        """Create a new document metadata record."""
        document_data["document_id"] = str(uuid.uuid4())
        document_data["created_at"] = datetime.now(timezone.utc).isoformat()
        document_data["updated_at"] = document_data["created_at"]
        document_data["extraction_status"] = "pending"

        self.metadata_table.put_item(Item=document_data)
        return document_data

    def get_document(self, document_id: str) -> Optional[dict]:
        """Get document metadata by ID."""
        response = self.metadata_table.get_item(Key={"document_id": document_id})
        return response.get("Item")

    def list_documents_by_claim(self, claim_id: str) -> list:
        """List all documents for a specific claim."""
        response = self.metadata_table.query(
            IndexName="claim_id-index",
            KeyConditionExpression="claim_id = :cid",
            ExpressionAttributeValues={":cid": claim_id},
        )
        return response.get("Items", [])

    def update_extraction_status(self, document_id: str, status: str) -> Optional[dict]:
        """Update the extraction status of a document."""
        response = self.metadata_table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="SET extraction_status = :s, updated_at = :u",
            ExpressionAttributeValues={
                ":s": status,
                ":u": datetime.now(timezone.utc).isoformat(),
            },
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def delete_document(self, document_id: str) -> None:
        """Delete document metadata."""
        self.metadata_table.delete_item(Key={"document_id": document_id})

    def save_extracted_data(self, extracted_data: dict) -> dict:
        """Save extracted data for a document."""
        extracted_data["extracted_at"] = datetime.now(timezone.utc).isoformat()
        self.extracted_table.put_item(Item=extracted_data)
        return extracted_data

    def get_extracted_data(self, document_id: str) -> Optional[dict]:
        """Get extracted data for a document."""
        response = self.extracted_table.get_item(Key={"document_id": document_id})
        return response.get("Item")

    def delete_extracted_data(self, document_id: str) -> None:
        """Delete extracted data for a document."""
        self.extracted_table.delete_item(Key={"document_id": document_id})
