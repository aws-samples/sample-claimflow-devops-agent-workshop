"""Claim Service Stack — ECS Fargate service for claim lifecycle management."""

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


class ClaimServiceStack(Stack):
    """Claim Service — core claim lifecycle management and orchestration."""

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
        claims_table_arn: str,
        claim_history_table_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecs_config = config["ecs"]
        sd_namespace = config["service_discovery"]["namespace"]

        self.service_construct = FargateServiceConstruct(
            self,
            "ClaimService",
            cluster=cluster,
            service_name="claim-service",
            docker_image_path="../services/claim-service",
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
                "CLAIMS_TABLE": f"{config['project_name']}-claims",
                "CLAIM_HISTORY_TABLE": f"{config['project_name']}-claim-history",
                "AUTH_SERVICE_URL": f"http://auth-service.{sd_namespace}:8000",
                "FRAUD_SERVICE_URL": f"http://fraud-service.{sd_namespace}:8000",
                "DOCUMENT_SERVICE_URL": f"http://document-service.{sd_namespace}:8000",
                "RULES_SERVICE_URL": f"http://rules-service.{sd_namespace}:8000",
                "NOTIFICATION_SERVICE_URL": f"http://notification-service.{sd_namespace}:8000",
            },
        )

        # IAM permissions — DynamoDB access for claims and claim-history tables
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                resources=[
                    claims_table_arn,
                    f"{claims_table_arn}/index/*",
                    claim_history_table_arn,
                    f"{claim_history_table_arn}/index/*",
                ],
            )
        )

        # Service discovery permissions
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["servicediscovery:DiscoverInstances"],
                resources=["*"],
            )
        )
