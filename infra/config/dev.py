"""Development environment configuration."""

CONFIG = {
    "environment": "dev",
    "aws_region": "us-east-1",
    "project_name": "claim-processing",
    "vpc": {
        "cidr": "10.0.0.0/16",
        "max_azs": 2,
        "nat_gateways": 1,
    },
    "ecs": {
        "cpu": 512,
        "memory_limit_mib": 1024,
        "desired_count": 1,
        "min_capacity": 1,
        "max_capacity": 3,
        "cpu_scaling_target": 70,
    },
    "aurora": {
        "instance_class": "t4g.medium",
        "database_name": "claims_analytics",
        "backup_retention_days": 7,
    },
    "api_gateway": {
        "throttle_rate_limit": 500,
        "throttle_burst_limit": 1000,
        "stage_name": "v1",
    },
    "dynamodb": {
        "billing_mode": "PAY_PER_REQUEST",
        "point_in_time_recovery": True,
    },
    "monitoring": {
        "log_retention_days": 30,
        "ecs_cpu_alarm_threshold": 80,
        "ecs_memory_alarm_threshold": 80,
        "api_5xx_alarm_threshold": 1,
    },
    "s3": {
        "documents_bucket_prefix": "claim-processing-documents",
        "frontend_bucket_prefix": "claim-processing-frontend",
    },
    "ses": {
        "sender_email": "noreply@claimprocessing.com",
    },
    "service_discovery": {
        "namespace": "claim-processing.local",
    },
}
