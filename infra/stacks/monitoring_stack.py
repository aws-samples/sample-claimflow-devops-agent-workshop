"""Monitoring Stack — CloudWatch log groups, SNS topic, DevOps Agent webhook Lambda."""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_logs as logs,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct


class MonitoringStack(Stack):
    """Observability infrastructure — logging, alerting, and the DevOps Agent bridge.

    Deploys:
    - One CloudWatch Log Group per backend service and one for API Gateway
    - An SNS topic that alarms fan out through
    - A Secrets Manager secret holding the DevOps Agent webhook HMAC shared secret
    - An AWS Lambda function subscribed to the SNS topic that HMAC-signs each
      alarm payload and POSTs it to the DevOps Agent webhook URL

    The webhook URL is a Lambda environment variable (URLs are not secrets).
    The HMAC secret is read from Secrets Manager at Lambda invocation time so
    the value can be rotated without redeploying the stack. Both are seeded
    with placeholders and updated by the participant after they create the
    webhook in the DevOps Agent console.
    """

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_name = config["project_name"]
        devops_agent_webhook_url = self.node.try_get_context("devops_agent_webhook_url") or ""
        devops_agent_webhook_secret = self.node.try_get_context("devops_agent_webhook_secret") or ""

        # =============================================
        # SNS Topic for Alarm Notifications
        # =============================================
        # Exposed as self.alarm_topic so AlarmsStack can subscribe alarms to it.
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=f"{project_name}-alarms",
            display_name="ClaimFlow CloudWatch Alarms",
        )

        # =============================================
        # DevOps Agent Webhook Secret (in Secrets Manager)
        # =============================================
        # Deploy with placeholder values initially. After creating your DevOps
        # Agent space and webhook, update them:
        #   - Lambda console → ClaimFlow-DevOpsAgent-Webhook → Environment variables → WEBHOOK_URL
        #   - Secrets Manager → claim-processing/devops-agent-webhook-secret → edit value
        #
        # Or re-deploy with:
        #   cdk deploy claim-processing-monitoring \
        #     -c devops_agent_webhook_url="<your-url>" \
        #     -c devops_agent_webhook_secret="<your-secret>"

        effective_webhook_url = devops_agent_webhook_url or "PLACEHOLDER_UPDATE_AFTER_DEVOPS_AGENT_SETUP"
        effective_webhook_secret = devops_agent_webhook_secret or "PLACEHOLDER_UPDATE_AFTER_DEVOPS_AGENT_SETUP"

        webhook_secret = secretsmanager.Secret(
            self,
            "DevOpsAgentWebhookSecret",
            secret_name=f"{project_name}/devops-agent-webhook-secret",
            description="HMAC-SHA256 shared secret used to sign DevOps Agent webhook payloads. Update this value after creating your DevOps Agent webhook.",
            secret_string_value=cdk.SecretValue.unsafe_plain_text(effective_webhook_secret),
        )

        # =============================================
        # DevOps Agent Webhook Lambda
        # =============================================
        webhook_lambda = _lambda.Function(
            self,
            "DevOpsAgentWebhook",
            function_name="ClaimFlow-DevOpsAgent-Webhook",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="devops_agent_webhook.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "WEBHOOK_URL": effective_webhook_url,
                "WEBHOOK_SECRET_ARN": webhook_secret.secret_arn,
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
            description="Forwards ClaimFlow CloudWatch Alarms to AWS DevOps Agent for auto-investigation",
        )

        webhook_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:DescribeAlarms", "cloudwatch:DescribeAlarmHistory"],
                resources=["*"],
            )
        )
        webhook_secret.grant_read(webhook_lambda)

        # Subscribe the Lambda to the SNS topic so every alarm fans out to it.
        self.alarm_topic.add_subscription(sns_subs.LambdaSubscription(webhook_lambda))

        # =============================================
        # CloudWatch Log Groups (one per service + API Gateway)
        # =============================================
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

        self.api_gateway_log_group = logs.LogGroup(
            self,
            "ApiGatewayLogGroup",
            log_group_name=f"/{project_name}/api-gateway",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # =============================================
        # Outputs
        # =============================================
        CfnOutput(self, "SnsTopicArn", value=self.alarm_topic.topic_arn)
        CfnOutput(self, "WebhookLambdaName", value=webhook_lambda.function_name)
        CfnOutput(self, "WebhookSecretArn", value=webhook_secret.secret_arn)
