"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Analytics service configuration."""

    service_name: str = "analytics-service"
    environment: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins. Defaults to "*" for local
    # development; set CORS_ALLOWED_ORIGINS to the frontend origin in deployed
    # environments so credentialed cross-origin requests are scoped correctly.
    cors_allowed_origins: str = "*"

    # Aurora PostgreSQL
    aurora_host: str = "localhost"
    aurora_port: int = 5432
    aurora_database: str = "claims_analytics"
    aurora_secret_arn: str = ""

    # DynamoDB
    claims_table: str = "claim-processing-claims"
    aws_region: str = "us-east-1"

    # Service URLs (via Cloud Map service discovery)
    auth_service_url: str = "http://auth-service.claim-processing.local:8000"

    # QuickSight
    quicksight_dashboard_id: str = ""
    quicksight_account_id: str = ""

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
