"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Claim service configuration."""

    service_name: str = "claim-service"
    environment: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins. Defaults to "*" for local
    # development; set CORS_ALLOWED_ORIGINS to the frontend origin in deployed
    # environments so credentialed cross-origin requests are scoped correctly.
    cors_allowed_origins: str = "*"

    # DynamoDB
    claims_table: str = "claim-processing-claims"
    claim_history_table: str = "claim-processing-claim-history"
    aws_region: str = "us-east-1"

    # Service URLs (via Cloud Map service discovery)
    auth_service_url: str = "http://auth-service.claim-processing.local:8000"
    fraud_service_url: str = "http://fraud-service.claim-processing.local:8000"
    document_service_url: str = "http://document-service.claim-processing.local:8000"
    rules_service_url: str = "http://rules-service.claim-processing.local:8000"
    notification_service_url: str = "http://notification-service.claim-processing.local:8000"

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
