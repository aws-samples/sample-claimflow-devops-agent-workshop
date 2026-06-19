"""Token validation router — used by other services for auth verification."""

from fastapi import APIRouter

from app.models.token import TokenValidationRequest, TokenValidationResponse
from app.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(request: TokenValidationRequest):
    """Validate a JWT token (service-to-service endpoint)."""
    return auth_service.validate_token(request.token)
