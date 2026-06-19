"""Document service — upload to S3, trigger extraction."""

import logging
import uuid
from typing import Optional

import boto3
from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.models.document import DocumentResponse, ExtractedDataResponse, ExtractedEntity, ExtractedKeyPhrase
from app.repositories.document_repository import DocumentRepository
from app.services.comprehend_client import ComprehendClient
from app.services.textract_client import TextractClient

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles document upload, storage, and extraction orchestration."""

    def __init__(self):
        self.repo = DocumentRepository()
        self.textract = TextractClient()
        self.comprehend = ComprehendClient()
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        self.bucket = settings.documents_bucket

    def upload_document(
        self,
        user_id: str,
        claim_id: str,
        document_type: str,
        file: UploadFile,
        description: Optional[str] = None,
    ) -> DocumentResponse:
        """Upload a document to S3 and create metadata record."""
        # Generate S3 key
        file_ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
        s3_key = f"documents/{claim_id}/{uuid.uuid4()}.{file_ext}"

        # Upload to S3
        try:
            file_content = file.file.read()
            file_size = len(file_content)

            self.s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=file.content_type or "application/octet-stream",
            )
        except Exception as e:
            logger.warning(f"S3 upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload document",
            )

        # Create metadata record
        document_data = {
            "claim_id": claim_id,
            "user_id": user_id,
            "document_type": document_type,
            "file_name": file.filename,
            "file_size": file_size,
            "content_type": file.content_type or "application/octet-stream",
            "s3_key": s3_key,
            "description": description,
        }

        created = self.repo.create_document(document_data)

        # Trigger extraction asynchronously (in production, use SQS/EventBridge)
        self._trigger_extraction(created["document_id"], s3_key)

        return self._to_response(created)

    def get_document(self, document_id: str, user_id: str, user_role: str) -> DocumentResponse:
        """Get document metadata."""
        document = self._get_document_or_404(document_id)

        if user_role == "policyholder" and document["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return self._to_response(document)

    def get_extracted_data(self, document_id: str, user_id: str, user_role: str) -> ExtractedDataResponse:
        """Get extracted data for a document."""
        document = self._get_document_or_404(document_id)

        if user_role == "policyholder" and document["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        extracted = self.repo.get_extracted_data(document_id)
        if not extracted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extracted data not available yet",
            )

        return ExtractedDataResponse(
            document_id=extracted["document_id"],
            raw_text=extracted.get("raw_text", ""),
            entities=[
                ExtractedEntity(**e) for e in extracted.get("entities", [])
            ],
            key_phrases=[
                ExtractedKeyPhrase(**p) for p in extracted.get("key_phrases", [])
            ],
            extraction_confidence=float(extracted.get("extraction_confidence", 0.0)),
            extracted_at=extracted["extracted_at"],
        )

    def list_documents_by_claim(self, claim_id: str) -> list[DocumentResponse]:
        """List all documents for a claim."""
        documents = self.repo.list_documents_by_claim(claim_id)
        return [self._to_response(doc) for doc in documents]

    def delete_document(self, document_id: str, user_id: str, user_role: str) -> None:
        """Delete a document and its extracted data."""
        document = self._get_document_or_404(document_id)

        if user_role == "policyholder" and document["user_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Delete from S3
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=document["s3_key"])
        except Exception as e:
            logger.warning(f"Failed to delete S3 object: {e}")

        # Delete metadata and extracted data
        self.repo.delete_document(document_id)
        self.repo.delete_extracted_data(document_id)

    def _trigger_extraction(self, document_id: str, s3_key: str) -> None:
        """Trigger text extraction and entity recognition."""
        try:
            # Extract text using Textract
            textract_result = self.textract.detect_text(self.bucket, s3_key)
            raw_text = textract_result["raw_text"]
            confidence = textract_result["confidence"]

            # Detect entities and key phrases using Comprehend
            entities = self.comprehend.detect_entities(raw_text)
            key_phrases = self.comprehend.detect_key_phrases(raw_text)

            # Save extracted data
            extracted_data = {
                "document_id": document_id,
                "raw_text": raw_text,
                "entities": entities,
                "key_phrases": key_phrases,
                "extraction_confidence": confidence,
            }
            self.repo.save_extracted_data(extracted_data)

            # Update extraction status
            self.repo.update_extraction_status(document_id, "completed")

        except Exception as e:
            logger.error(f"Extraction failed for document {document_id}: {e}")
            self.repo.update_extraction_status(document_id, "failed")

    def _get_document_or_404(self, document_id: str) -> dict:
        """Get document or raise 404."""
        document = self.repo.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        return document

    def _to_response(self, document: dict) -> DocumentResponse:
        """Convert DynamoDB item to DocumentResponse."""
        return DocumentResponse(
            document_id=document["document_id"],
            claim_id=document["claim_id"],
            user_id=document["user_id"],
            document_type=document["document_type"],
            file_name=document["file_name"],
            file_size=int(document["file_size"]),
            content_type=document["content_type"],
            s3_key=document["s3_key"],
            description=document.get("description"),
            extraction_status=document.get("extraction_status", "pending"),
            created_at=document["created_at"],
            updated_at=document.get("updated_at"),
        )
