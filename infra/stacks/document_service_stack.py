"""Document Service Stack — ECS Fargate service with Textract, Comprehend, S3 access."""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_servicediscovery as sd,
)
from constructs import Construct
from shared_constructs.fargate_service import FargateServiceConstruct


class DocumentServiceStack(Stack):
    """Document Service — upload, OCR extraction, entity recognition."""

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
        document_metadata_table_arn: str,
        extracted_data_table_arn: str,
        documents_bucket: s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecs_config = config["ecs"]
        sd_namespace = config["service_discovery"]["namespace"]

        self.service_construct = FargateServiceConstruct(
            self,
            "DocumentService",
            cluster=cluster,
            service_name="document-service",
            docker_image_path="../services/document-service",
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
                "DOCUMENT_METADATA_TABLE": f"{config['project_name']}-document-metadata",
                "EXTRACTED_DATA_TABLE": f"{config['project_name']}-extracted-data",
                "DOCUMENTS_BUCKET": documents_bucket.bucket_name,
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
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                ],
                resources=[
                    document_metadata_table_arn,
                    f"{document_metadata_table_arn}/index/*",
                    extracted_data_table_arn,
                ],
            )
        )

        # IAM permissions — S3
        documents_bucket.grant_read_write(self.service_construct.task_role)

        # IAM permissions — Amazon Textract
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:AnalyzeDocument",
                    "textract:DetectDocumentText",
                    "textract:AnalyzeExpense",
                ],
                resources=["*"],
            )
        )

        # IAM permissions — Amazon Comprehend
        self.service_construct.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "comprehend:DetectEntities",
                    "comprehend:DetectKeyPhrases",
                    "comprehend:DetectSentiment",
                ],
                resources=["*"],
            )
        )
