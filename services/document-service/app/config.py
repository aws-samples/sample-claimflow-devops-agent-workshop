"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Document service configuration."""

    service_name: str = "document-service"
    environment: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins. Defaults to "*" for local
    # development; set CORS_ALLOWED_ORIGINS to the frontend origin in deployed
    # environments so credentialed cross-origin requests are scoped correctly.
    cors_allowed_origins: str = "*"

    # DynamoDB
    document_metadata_table: str = "claim-processing-document-metadata"
    extracted_data_table: str = "claim-processing-extracted-data"
    aws_region: str = "us-east-1"

    # S3
    documents_bucket: str = "claim-processing-documents-{account}"

    # Auth Service
    auth_service_url: str = "http://auth-service.claim-processing.local:8000"

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
