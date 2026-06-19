"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Notification service configuration."""

    service_name: str = "notification-service"
    environment: str = "dev"
    port: int = 8000
    log_level: str = "INFO"

    # CORS — comma-separated list of allowed origins. Defaults to "*" for local
    # development; set CORS_ALLOWED_ORIGINS to the frontend origin in deployed
    # environments so credentialed cross-origin requests are scoped correctly.
    cors_allowed_origins: str = "*"

    # DynamoDB
    notification_log_table: str = "claim-processing-notification-log"
    notification_preferences_table: str = "claim-processing-notification-preferences"
    aws_region: str = "us-east-1"

    # Auth Service
    auth_service_url: str = "http://auth-service.claim-processing.local:8000"

    # SES
    ses_sender_email: str = "noreply@claimprocessing.com"

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
