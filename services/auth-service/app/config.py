"""Application configuration from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Auth service configuration."""

    service_name: str = "auth-service"
    environment: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins. Defaults to "*" for local
    # development; set CORS_ALLOWED_ORIGINS to the frontend origin in deployed
    # environments so credentialed cross-origin requests are scoped correctly.
    cors_allowed_origins: str = "*"

    # DynamoDB
    users_table: str = "claim-processing-users"
    sessions_table: str = "claim-processing-sessions"
    aws_region: str = "us-east-1"

    # JWT
    # The signing key MUST be supplied via the JWT_SECRET_KEY environment
    # variable (sourced from AWS Secrets Manager in deployed environments).
    # When unset in local dev, an ephemeral random key is generated at startup
    # so the service runs without any key being committed to source.
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # SES
    ses_sender_email: str = "noreply@claimprocessing.com"

    # Seed three demo users (admin / adjudicator / policyholder) on startup if
    # they do not already exist. Idempotent. Set SEED_DEFAULT_USERS=false to
    # disable (e.g. for production-like environments).
    seed_default_users: bool = True

    class Config:
        env_prefix = ""
        case_sensitive = False

    @model_validator(mode="after")
    def _resolve_jwt_secret(self) -> "Settings":
        """Require a JWT key outside dev; generate an ephemeral one for local dev."""
        if not self.jwt_secret_key:
            if self.environment == "dev":
                import secrets

                self.jwt_secret_key = secrets.token_urlsafe(48)
            else:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong secret (e.g. from AWS "
                    "Secrets Manager) when ENVIRONMENT is not 'dev'."
                )
        return self


settings = Settings()
