"""Auth Service Stack — ECS Fargate service for authentication."""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_servicediscovery as sd,
)
from constructs import Construct
from shared_constructs.fargate_service import FargateServiceConstruct


class AuthServiceStack(Stack):
    """Auth Service — user authentication, JWT tokens, RBAC."""

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
        users_table_arn: str,
        sessions_table_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecs_config = config["ecs"]

        # JWT signing key — generated and stored in AWS Secrets Manager rather
        # than baked into the image or passed as a plaintext environment
        # variable. ECS injects it into the container at launch time.
        self.jwt_secret = secretsmanager.Secret(
            self,
            "JwtSigningKey",
            description="JWT signing key for the auth service",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=48,
                exclude_punctuation=True,
            ),
        )

        self.service_construct = FargateServiceConstruct(
            self,
            "AuthService",
            cluster=cluster,
            service_name="auth-service",
            docker_image_path="../services/auth-service",
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
                "USERS_TABLE": f"{config['project_name']}-users",
                "SESSIONS_TABLE": f"{config['project_name']}-sessions",
            },
            secrets={
                "JWT_SECRET_KEY": ecs.Secret.from_secrets_manager(self.jwt_secret),
            },
        )

        # IAM permissions — DynamoDB access for users and sessions tables
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
                    users_table_arn,
                    f"{users_table_arn}/index/*",
                    sessions_table_arn,
                    f"{sessions_table_arn}/index/*",
                ],
            )
        )

        # SES permissions for password reset emails.
        # Scoped to the configured sender identity rather than all identities.
        ses_sender_email = config.get("ses", {}).get("sender_email", "noreply@claimprocessing.com")
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=[
                    f"arn:aws:ses:{self.region}:{self.account}:identity/{ses_sender_email}",
                ],
            )
        )
