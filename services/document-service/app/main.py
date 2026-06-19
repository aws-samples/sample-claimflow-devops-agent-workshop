"""FastAPI application entry point for Document Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import document_router

app = FastAPI(
    title="Document Service",
    description="Document upload, storage, OCR extraction, and entity recognition",
    version="1.0.0",
)

# CORS is configured from the CORS_ALLOWED_ORIGINS environment variable as a
# comma-separated list of origins (e.g. "https://example.cloudfront.net").
# Credentials are only allowed when explicit origins are configured, since the
# CORS spec forbids combining allow_credentials=True with a wildcard origin.
_cors_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
_allow_credentials = _cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(document_router.router, prefix="/api/documents", tags=["Documents"])


@app.get("/health")
async def health_check():
    """Health check endpoint for ECS."""
    return {"status": "healthy", "service": settings.service_name}
