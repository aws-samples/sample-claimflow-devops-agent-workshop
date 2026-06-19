"""Monitoring Stack — CloudWatch log groups, X-Ray, alarms, SNS topic."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_logs as logs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
)
from constructs import Construct


class MonitoringStack(Stack):
    """Observability infrastructure — logging, tracing, and alerting."""

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        monitoring_config = config["monitoring"]
        project_name = config["project_name"]

        # SNS topic for alarms
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=f"{project_name}-alarms",
            display_name="Claim Processing Alarms",
        )

        # CloudWatch Log Groups (one per service)
        service_names = [
            "auth-service",
            "claim-service",
            "fraud-service",
            "document-service",
            "notification-service",
            "rules-service",
            "analytics-service",
        ]

        self.log_groups = {}
        for service_name in service_names:
            self.log_groups[service_name] = logs.LogGroup(
                self,
                f"LogGroup-{service_name}",
                log_group_name=f"/{project_name}/{service_name}",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            )

        # API Gateway log group
        self.api_gateway_log_group = logs.LogGroup(
            self,
            "ApiGatewayLogGroup",
            log_group_name=f"/{project_name}/api-gateway",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
