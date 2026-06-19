"""Tests for document service business logic."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

from fastapi import HTTPException, UploadFile

from app.services.document_service import DocumentService


@pytest.fixture
def document_service():
    """Create DocumentService with mocked dependencies."""
    with patch("app.services.document_service.DocumentRepository") as mock_repo, \
         patch("app.services.document_service.TextractClient") as mock_textract, \
         patch("app.services.document_service.ComprehendClient") as mock_comprehend, \
         patch("app.services.document_service.boto3") as mock_boto3:
        service = DocumentService()
        service.repo = mock_repo.return_value
        service.textract = mock_textract.return_value
        service.comprehend = mock_comprehend.return_value
        service.s3 = mock_boto3.client.return_value
        yield service


def test_upload_document_success(document_service):
    """Uploading a document should create metadata and trigger extraction."""
    document_service.repo.create_document.return_value = {
        "document_id": "doc-123",
        "claim_id": "claim-456",
        "user_id": "user1",
        "document_type": "medical_report",
        "file_name": "report.pdf",
        "file_size": 1024,
        "content_type": "application/pdf",
        "s3_key": "documents/claim-456/abc.pdf",
        "description": "Medical report",
        "extraction_status": "pending",
        "created_at": "2025-05-25T00:00:00Z",
    }
    document_service.textract.detect_text.return_value = {
        "raw_text": "Sample text",
        "confidence": 0.95,
    }
    document_service.comprehend.detect_entities.return_value = []
    document_service.comprehend.detect_key_phrases.return_value = []
    document_service.repo.save_extracted_data.return_value = {}
    document_service.repo.update_extraction_status.return_value = {}

    # Create a mock UploadFile
    file = MagicMock()
    file.filename = "report.pdf"
    file.content_type = "application/pdf"
    file.file.read.return_value = b"fake pdf content"

    result = document_service.upload_document(
        user_id="user1",
        claim_id="claim-456",
        document_type="medical_report",
        file=file,
        description="Medical report",
    )

    assert result.document_id == "doc-123"
    assert result.claim_id == "claim-456"
    assert result.document_type == "medical_report"
    document_service.s3.put_object.assert_called_once()


def test_get_document_not_found(document_service):
    """Getting a non-existent document should raise 404."""
    document_service.repo.get_document.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        document_service.get_document("nonexistent", "user1", "policyholder")
    assert exc_info.value.status_code == 404


def test_get_document_access_denied(document_service):
    """Policyholder accessing another user's document should raise 403."""
    document_service.repo.get_document.return_value = {
        "document_id": "doc-123",
        "claim_id": "claim-456",
        "user_id": "user2",
        "document_type": "medical_report",
        "file_name": "report.pdf",
        "file_size": 1024,
        "content_type": "application/pdf",
        "s3_key": "documents/claim-456/abc.pdf",
        "extraction_status": "completed",
        "created_at": "2025-05-25T00:00:00Z",
    }

    with pytest.raises(HTTPException) as exc_info:
        document_service.get_document("doc-123", "user1", "policyholder")
    assert exc_info.value.status_code == 403


def test_get_extracted_data_not_available(document_service):
    """Getting extracted data before extraction completes should raise 404."""
    document_service.repo.get_document.return_value = {
        "document_id": "doc-123",
        "claim_id": "claim-456",
        "user_id": "user1",
        "document_type": "medical_report",
        "file_name": "report.pdf",
        "file_size": 1024,
        "content_type": "application/pdf",
        "s3_key": "documents/claim-456/abc.pdf",
        "extraction_status": "pending",
        "created_at": "2025-05-25T00:00:00Z",
    }
    document_service.repo.get_extracted_data.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        document_service.get_extracted_data("doc-123", "user1", "policyholder")
    assert exc_info.value.status_code == 404


def test_delete_document_success(document_service):
    """Deleting a document should remove S3 object and metadata."""
    document_service.repo.get_document.return_value = {
        "document_id": "doc-123",
        "claim_id": "claim-456",
        "user_id": "user1",
        "document_type": "medical_report",
        "file_name": "report.pdf",
        "file_size": 1024,
        "content_type": "application/pdf",
        "s3_key": "documents/claim-456/abc.pdf",
        "extraction_status": "completed",
        "created_at": "2025-05-25T00:00:00Z",
    }

    document_service.delete_document("doc-123", "user1", "policyholder")

    document_service.s3.delete_object.assert_called_once()
    document_service.repo.delete_document.assert_called_once_with("doc-123")
    document_service.repo.delete_extracted_data.assert_called_once_with("doc-123")
