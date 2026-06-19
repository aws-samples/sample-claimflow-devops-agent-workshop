"""Notification Service Stack — ECS Fargate service with SES and SNS access."""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_servicediscovery as sd,
)
from constructs import Construct
from shared_constructs.fargate_service import FargateServiceConstruct


class NotificationServiceStack(Stack):
    """Notification Service — email (SES) and SMS (SNS) delivery."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        vpc: ec2.Vpc,
        cluster: ecs.Cluster,
        security_group: ec2.SecurityGroup,
        cloud_map_namespace: sd.PrivateDnsNamespace,
        log_group: logs.LogGroup,
        notification_log_table_arn: str,
        notification_preferences_table_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecs_config = config["ecs"]
        sd_namespace = config["service_discovery"]["namespace"]

        self.service_construct = FargateServiceConstruct(
            self,
            "NotificationService",
            cluster=cluster,
            service_name="notification-service",
            docker_image_path="../services/notification-service",
            vpc=vpc,
            security_group=security_group,
            cloud_map_namespace=cloud_map_namespace,
            log_group=log_group,
            cpu=ecs_config["cpu"],
            memory_limit_mib=ecs_config["memory_limit_mib"],
            desired_count=ecs_config["desired_count"],
            min_capacity=ecs_config["min_capacity"],
            max_capacity=ecs_config["max_capacity"],
            cpu_scaling_target=ecs_config["cpu_scaling_target"],
            environment={
                "NOTIFICATION_LOG_TABLE": f"{config['project_name']}-notification-log",
                "NOTIFICATION_PREFERENCES_TABLE": f"{config['project_name']}-notification-preferences",
                "AUTH_SERVICE_URL": f"http://auth-service.{sd_namespace}:8000",
            },
        )

        # IAM permissions — DynamoDB
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                ],
                resources=[
                    notification_log_table_arn,
                    f"{notification_log_table_arn}/index/*",
                    notification_preferences_table_arn,
                ],
            )
        )

        # IAM permissions — Amazon SES
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"],
            )
        )

        # IAM permissions — Amazon SNS (SMS)
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sns:Publish"],
                resources=["*"],
            )
        )
