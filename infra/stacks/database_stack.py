"""Database Stack — DynamoDB tables and Aurora PostgreSQL cluster."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_dynamodb as dynamodb,
    aws_rds as rds,
    aws_ec2 as ec2,
)
from constructs import Construct
from shared_constructs.dynamodb_table import DynamoDBTableConstruct


class DatabaseStack(Stack):
    """All database resources — DynamoDB tables and Aurora PostgreSQL."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        vpc: ec2.Vpc,
        database_security_group: ec2.SecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        db_config = config["dynamodb"]
        aurora_config = config["aurora"]

        # --- DynamoDB Tables ---

        # Claims table
        self.claims_table = DynamoDBTableConstruct(
            self,
            "ClaimsTable",
            table_name=f"{config['project_name']}-claims",
            partition_key=dynamodb.Attribute(name="claim_id", type=dynamodb.AttributeType.STRING),
            point_in_time_recovery=db_config["point_in_time_recovery"],
        )
        self.claims_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
        )
        self.claims_table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
        )
        self.claims_table.add_global_secondary_index(
            index_name="type-index",
            partition_key=dynamodb.Attribute(name="claim_type", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
        )

        # Claim history table
        self.claim_history_table = DynamoDBTableConstruct(
            self,
            "ClaimHistoryTable",
            table_name=f"{config['project_name']}-claim-history",
            partition_key=dynamodb.Attribute(name="claim_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
        )

        # Fraud scores table
        self.fraud_scores_table = DynamoDBTableConstruct(
            self,
            "FraudScoresTable",
            table_name=f"{config['project_name']}-fraud-scores",
            partition_key=dynamodb.Attribute(name="claim_id", type=dynamodb.AttributeType.STRING),
        )
        self.fraud_scores_table.add_global_secondary_index(
            index_name="risk-level-index",
            partition_key=dynamodb.Attribute(name="risk_level", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
        )

        # Fraud patterns table
        self.fraud_patterns_table = DynamoDBTableConstruct(
            self,
            "FraudPatternsTable",
            table_name=f"{config['project_name']}-fraud-patterns",
            partition_key=dynamodb.Attribute(name="pattern_id", type=dynamodb.AttributeType.STRING),
        )

        # Document metadata table
        self.document_metadata_table = DynamoDBTableConstruct(
            self,
            "DocumentMetadataTable",
            table_name=f"{config['project_name']}-document-metadata",
            partition_key=dynamodb.Attribute(name="document_id", type=dynamodb.AttributeType.STRING),
        )
        self.document_metadata_table.add_global_secondary_index(
            index_name="claim_id-index",
            partition_key=dynamodb.Attribute(name="claim_id", type=dynamodb.AttributeType.STRING),
        )

        # Extracted data table
        self.extracted_data_table = DynamoDBTableConstruct(
            self,
            "ExtractedDataTable",
            table_name=f"{config['project_name']}-extracted-data",
            partition_key=dynamodb.Attribute(name="document_id", type=dynamodb.AttributeType.STRING),
        )

        # Notification log table
        self.notification_log_table = DynamoDBTableConstruct(
            self,
            "NotificationLogTable",
            table_name=f"{config['project_name']}-notification-log",
            partition_key=dynamodb.Attribute(name="notification_id", type=dynamodb.AttributeType.STRING),
        )
        self.notification_log_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sent_at", type=dynamodb.AttributeType.STRING),
        )
        self.notification_log_table.add_global_secondary_index(
            index_name="claim_id-index",
            partition_key=dynamodb.Attribute(name="claim_id", type=dynamodb.AttributeType.STRING),
        )

        # Notification preferences table
        self.notification_preferences_table = DynamoDBTableConstruct(
            self,
            "NotificationPreferencesTable",
            table_name=f"{config['project_name']}-notification-preferences",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
        )

        # Users table
        self.users_table = DynamoDBTableConstruct(
            self,
            "UsersTable",
            table_name=f"{config['project_name']}-users",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
        )
        self.users_table.add_global_secondary_index(
            index_name="email-index",
            partition_key=dynamodb.Attribute(name="email", type=dynamodb.AttributeType.STRING),
        )

        # Sessions table
        self.sessions_table = DynamoDBTableConstruct(
            self,
            "SessionsTable",
            table_name=f"{config['project_name']}-sessions",
            partition_key=dynamodb.Attribute(name="session_id", type=dynamodb.AttributeType.STRING),
        )
        self.sessions_table.add_global_secondary_index(
            index_name="user_id-index",
            partition_key=dynamodb.Attribute(name="user_id", type=dynamodb.AttributeType.STRING),
        )

        # Rules table
        self.rules_table = DynamoDBTableConstruct(
            self,
            "RulesTable",
            table_name=f"{config['project_name']}-rules",
            partition_key=dynamodb.Attribute(name="rule_id", type=dynamodb.AttributeType.STRING),
        )
        self.rules_table.add_global_secondary_index(
            index_name="claim_type-index",
            partition_key=dynamodb.Attribute(name="claim_type", type=dynamodb.AttributeType.STRING),
        )

        # Rule results table
        self.rule_results_table = DynamoDBTableConstruct(
            self,
            "RuleResultsTable",
            table_name=f"{config['project_name']}-rule-results",
            partition_key=dynamodb.Attribute(name="claim_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="rule_id", type=dynamodb.AttributeType.STRING),
        )

        # --- Aurora PostgreSQL ---

        self.aurora_cluster = rds.DatabaseCluster(
            self,
            "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.of("16.8", "16"),
            ),
            default_database_name=aurora_config["database_name"],
            writer=rds.ClusterInstance.provisioned(
                "Writer",
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MEDIUM
                ),
            ),
            readers=[
                rds.ClusterInstance.provisioned(
                    "Reader",
                    instance_type=ec2.InstanceType.of(
                        ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MEDIUM
                    ),
                ),
            ],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[database_security_group],
            backup=rds.BackupProps(retention=Duration.days(aurora_config["backup_retention_days"])),
            removal_policy=RemovalPolicy.DESTROY,
            storage_encrypted=True,
        )
