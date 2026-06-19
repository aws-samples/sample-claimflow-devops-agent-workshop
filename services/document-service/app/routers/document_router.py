"""Document router — all document management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.middleware.auth_middleware import get_current_user
from app.models.document import DocumentResponse, ExtractedDataResponse
from app.services.document_service import DocumentService

router = APIRouter()
document_service = DocumentService()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    claim_id: str = Form(...),
    document_type: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a document for a claim."""
    return document_service.upload_document(
        user_id=current_user["user_id"],
        claim_id=claim_id,
        document_type=document_type,
        file=file,
        description=description,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get document metadata by ID."""
    return document_service.get_document(
        document_id, current_user["user_id"], current_user["role"]
    )


@router.get("/{document_id}/extracted", response_model=ExtractedDataResponse)
async def get_extracted_data(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get extracted data (OCR text, entities, key phrases) for a document."""
    return document_service.get_extracted_data(
        document_id, current_user["user_id"], current_user["role"]
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    claim_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """List all documents for a claim."""
    return document_service.list_documents_by_claim(claim_id)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a document."""
    document_service.delete_document(
        document_id, current_user["user_id"], current_user["role"]
    )
