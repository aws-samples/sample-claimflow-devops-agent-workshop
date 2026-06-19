"""FastAPI application entry point for Auth Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth_router, user_router, validation_router

app = FastAPI(
    title="Auth Service",
    description="User authentication, JWT tokens, and role-based access control",
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

app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_router.router, prefix="/api/auth/users", tags=["User Management"])
app.include_router(validation_router.router, prefix="/api/auth", tags=["Token Validation"])


@app.on_event("startup")
async def _seed_default_users() -> None:
    """Seed demo users on startup (idempotent; gated by SEED_DEFAULT_USERS)."""
    if not settings.seed_default_users:
        return
    # Imported lazily so the rest of the app starts even if seeding deps fail.
    from app.services.seed_service import seed_default_users

    seed_default_users()


@app.get("/health")
async def health_check():
    """Health check endpoint for ECS."""
    return {"status": "healthy", "service": settings.service_name}
