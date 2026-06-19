"""Document data models and schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    """Metadata for document upload request."""

    claim_id: str = Field(..., min_length=1)
    document_type: str = Field(..., min_length=1)
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    """Response schema for document metadata."""

    document_id: str
    claim_id: str
    user_id: str
    document_type: str
    file_name: str
    file_size: int
    content_type: str
    s3_key: str
    description: Optional[str] = None
    extraction_status: str = "pending"
    created_at: str
    updated_at: Optional[str] = None


class ExtractedEntity(BaseModel):
    """A single extracted entity from document."""

    text: str
    entity_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ExtractedKeyPhrase(BaseModel):
    """A single extracted key phrase from document."""

    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ExtractedDataResponse(BaseModel):
    """Response schema for extracted document data."""

    document_id: str
    raw_text: str
    entities: list[ExtractedEntity] = []
    key_phrases: list[ExtractedKeyPhrase] = []
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_at: str
