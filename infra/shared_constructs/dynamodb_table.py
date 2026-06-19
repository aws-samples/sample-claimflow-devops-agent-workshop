"""Reusable DynamoDB table construct."""

from constructs import Construct
from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
)


class DynamoDBTableConstruct(Construct):
    """Common DynamoDB table pattern with standard configuration."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table_name: str,
        partition_key: dynamodb.Attribute,
        sort_key: dynamodb.Attribute = None,
        billing_mode: dynamodb.BillingMode = dynamodb.BillingMode.PAY_PER_REQUEST,
        point_in_time_recovery: bool = True,
        removal_policy: RemovalPolicy = RemovalPolicy.DESTROY,
    ) -> None:
        super().__init__(scope, construct_id)

        self.table = dynamodb.Table(
            self,
            "Table",
            table_name=table_name,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
            point_in_time_recovery=point_in_time_recovery,
            removal_policy=removal_policy,
        )

    def add_global_secondary_index(
        self,
        index_name: str,
        partition_key: dynamodb.Attribute,
        sort_key: dynamodb.Attribute = None,
    ) -> None:
        """Add a GSI to the table."""
        self.table.add_global_secondary_index(
            index_name=index_name,
            partition_key=partition_key,
            sort_key=sort_key,
        )
