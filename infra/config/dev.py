"""Development environment configuration."""

CONFIG = {
    "environment": "dev",
    "aws_region": "us-east-1",
    "project_name": "claim-processing",
    "vpc": {
        "cidr": "10.0.0.0/16",
        # Span all Availability Zones in the region (us-east-1 has 6: a-f) so the
        # Aurora DB subnet group can place in whichever AZ has instance-class
        # capacity. The capacity error that motivated this had capacity only in
        # us-east-1d/1f, which a 2- or 3-AZ VPC never reaches. CDK caps this at
        # the number of AZs actually available, and requires an account-aware
        # stack (see app.py) because environment-agnostic stacks are limited to
        # 2 AZs. More AZs add a few extra interface-endpoint ENIs (minor cost).
        "max_azs": 6,
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
        # Aurora writer/reader instance class (now wired through to
        # database_stack.py). If a deploy fails with an Availability-Zone
        # capacity error for this class, switch to another broadly-available
        # class and redeploy, e.g. "t3.medium", "r6g.large", or "r6g.xlarge".
        # Aurora provisioned instances take a single class, so there is no
        # automatic multi-type fallback; combined with the multi-AZ VPC this is
        # the fast manual recovery lever.
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
        "ecs_cpu_alarm_threshold": 50,
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
