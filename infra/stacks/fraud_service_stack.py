"""Fraud Detection Service Stack — ECS Fargate service with Bedrock access."""

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


class FraudServiceStack(Stack):
    """Fraud Detection Service — AI-powered fraud analysis via Amazon Bedrock."""

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
        fraud_scores_table_arn: str,
        fraud_patterns_table_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecs_config = config["ecs"]
        sd_namespace = config["service_discovery"]["namespace"]

        self.service_construct = FargateServiceConstruct(
            self,
            "FraudService",
            cluster=cluster,
            service_name="fraud-service",
            docker_image_path="../services/fraud-service",
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
                "FRAUD_SCORES_TABLE": f"{config['project_name']}-fraud-scores",
                "FRAUD_PATTERNS_TABLE": f"{config['project_name']}-fraud-patterns",
                "AUTH_SERVICE_URL": f"http://auth-service.{sd_namespace}:8000",
                "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
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
                    "dynamodb:Scan",
                ],
                resources=[
                    fraud_scores_table_arn,
                    f"{fraud_scores_table_arn}/index/*",
                    fraud_patterns_table_arn,
                ],
            )
        )

        # IAM permissions — Amazon Bedrock.
        # Claude Sonnet 4.5 is invoked through the US cross-Region inference
        # profile, which routes requests to the foundation model in any of the
        # US commercial Regions. The task role therefore needs InvokeModel on
        # both the inference profile and the underlying foundation models.
        model_name = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        inference_profile = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        bedrock_regions = ["us-east-1", "us-east-2", "us-west-2"]
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/{inference_profile}",
                ]
                + [
                    f"arn:aws:bedrock:{r}::foundation-model/{model_name}"
                    for r in bedrock_regions
                ],
            )
        )
