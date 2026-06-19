"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Fraud service configuration."""

    service_name: str = "fraud-service"
    environment: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins. Defaults to "*" for local
    # development; set CORS_ALLOWED_ORIGINS to the frontend origin in deployed
    # environments so credentialed cross-origin requests are scoped correctly.
    cors_allowed_origins: str = "*"

    # DynamoDB
    fraud_scores_table: str = "claim-processing-fraud-scores"
    fraud_patterns_table: str = "claim-processing-fraud-patterns"
    aws_region: str = "us-east-1"

    # Auth Service
    auth_service_url: str = "http://auth-service.claim-processing.local:8000"

    # Bedrock — Claude Sonnet 4.5 via the US cross-Region inference profile.
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # Fraud threshold
    fraud_threshold: int = 70

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
