#!/usr/bin/env python3
"""CDK App entry point — Claim Processing Services infrastructure."""

import os

import aws_cdk as cdk

from config.dev import CONFIG
from stacks.network_stack import NetworkStack
from stacks.database_stack import DatabaseStack
from stacks.storage_stack import StorageStack
from stacks.monitoring_stack import MonitoringStack
from stacks.auth_service_stack import AuthServiceStack
from stacks.claim_service_stack import ClaimServiceStack
from stacks.fraud_service_stack import FraudServiceStack
from stacks.document_service_stack import DocumentServiceStack
from stacks.notification_service_stack import NotificationServiceStack
from stacks.rules_service_stack import RulesServiceStack
from stacks.analytics_service_stack import AnalyticsServiceStack
from stacks.api_gateway_stack import ApiGatewayStack
from stacks.frontend_stack import FrontendStack
from stacks.alarms_stack import AlarmsStack

app = cdk.App()

env = cdk.Environment(region=CONFIG["aws_region"])
project = CONFIG["project_name"]

# ─────────────────────────────────────────────────
# Uniform Tags — Applied to ALL resources across ALL stacks
# ─────────────────────────────────────────────────
cdk.Tags.of(app).add("Project", "claim-processing")
cdk.Tags.of(app).add("Application", "ClaimFlow")
cdk.Tags.of(app).add("Environment", "dev")
cdk.Tags.of(app).add("ManagedBy", "aws-cdk")
cdk.Tags.of(app).add("auto-delete", "no")

# Phase 1: Foundation
network_stack = NetworkStack(app, f"{project}-network", config=CONFIG, env=env)
monitoring_stack = MonitoringStack(app, f"{project}-monitoring", config=CONFIG, env=env)

# Phase 2: Data and Storage
database_stack = DatabaseStack(
    app,
    f"{project}-database",
    config=CONFIG,
    vpc=network_stack.vpc,
    database_security_group=network_stack.database_security_group,
    env=env,
)
database_stack.add_dependency(network_stack)

storage_stack = StorageStack(app, f"{project}-storage", config=CONFIG, env=env)

# ECS Cluster (shared across all services — created in NetworkStack)
ecs_cluster = network_stack.ecs_cluster

# Phase 3: Auth Service (all services depend on this)
auth_service_stack = AuthServiceStack(
    app,
    f"{project}-auth-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["auth-service"],
    users_table_arn=database_stack.users_table.table.table_arn,
    sessions_table_arn=database_stack.sessions_table.table.table_arn,
    env=env,
)
auth_service_stack.add_dependency(database_stack)
auth_service_stack.add_dependency(monitoring_stack)

# Phase 4: Application Services (can be parallel)
claim_service_stack = ClaimServiceStack(
    app,
    f"{project}-claim-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["claim-service"],
    claims_table_arn=database_stack.claims_table.table.table_arn,
    claim_history_table_arn=database_stack.claim_history_table.table.table_arn,
    env=env,
)
claim_service_stack.add_dependency(auth_service_stack)

fraud_service_stack = FraudServiceStack(
    app,
    f"{project}-fraud-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["fraud-service"],
    fraud_scores_table_arn=database_stack.fraud_scores_table.table.table_arn,
    fraud_patterns_table_arn=database_stack.fraud_patterns_table.table.table_arn,
    env=env,
)
fraud_service_stack.add_dependency(auth_service_stack)

document_service_stack = DocumentServiceStack(
    app,
    f"{project}-document-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["document-service"],
    document_metadata_table_arn=database_stack.document_metadata_table.table.table_arn,
    extracted_data_table_arn=database_stack.extracted_data_table.table.table_arn,
    documents_bucket=storage_stack.documents_bucket,
    env=env,
)
document_service_stack.add_dependency(auth_service_stack)
document_service_stack.add_dependency(storage_stack)

notification_service_stack = NotificationServiceStack(
    app,
    f"{project}-notification-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["notification-service"],
    notification_log_table_arn=database_stack.notification_log_table.table.table_arn,
    notification_preferences_table_arn=database_stack.notification_preferences_table.table.table_arn,
    env=env,
)
notification_service_stack.add_dependency(auth_service_stack)

rules_service_stack = RulesServiceStack(
    app,
    f"{project}-rules-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["rules-service"],
    rules_table_arn=database_stack.rules_table.table.table_arn,
    rule_results_table_arn=database_stack.rule_results_table.table.table_arn,
    env=env,
)
rules_service_stack.add_dependency(auth_service_stack)

analytics_service_stack = AnalyticsServiceStack(
    app,
    f"{project}-analytics-service",
    config=CONFIG,
    vpc=network_stack.vpc,
    cluster=ecs_cluster,
    security_group=network_stack.ecs_security_group,
    cloud_map_namespace=network_stack.cloud_map_namespace,
    log_group=monitoring_stack.log_groups["analytics-service"],
    aurora_cluster=database_stack.aurora_cluster,
    claims_table_arn=database_stack.claims_table.table.table_arn,
    env=env,
)
analytics_service_stack.add_dependency(auth_service_stack)

# Phase 4b: Alarms — runs after every service stack so it can consume each
# FargateService's ServiceName token via metric dimensions_map. All alarms
# fan out through the SNS topic in MonitoringStack to the DevOps Agent
# webhook Lambda.
alarms_stack = AlarmsStack(
    app,
    f"{project}-alarms",
    config=CONFIG,
    alarm_topic=monitoring_stack.alarm_topic,
    services={
        "auth-service": auth_service_stack.service_construct.service,
        "claim-service": claim_service_stack.service_construct.service,
        "fraud-service": fraud_service_stack.service_construct.service,
        "document-service": document_service_stack.service_construct.service,
        "notification-service": notification_service_stack.service_construct.service,
        "rules-service": rules_service_stack.service_construct.service,
        "analytics-service": analytics_service_stack.service_construct.service,
    },
    env=env,
)
alarms_stack.add_dependency(auth_service_stack)
alarms_stack.add_dependency(claim_service_stack)
alarms_stack.add_dependency(fraud_service_stack)
alarms_stack.add_dependency(document_service_stack)
alarms_stack.add_dependency(notification_service_stack)
alarms_stack.add_dependency(rules_service_stack)
alarms_stack.add_dependency(analytics_service_stack)

# Phase 5: API Gateway
# Map each API route to its backing ECS service. The API Gateway stack creates
# one NLB listener + target group per service and routes /api/<route>/* to it.
service_targets = {
    "claims": claim_service_stack.service_construct.service,
    "fraud": fraud_service_stack.service_construct.service,
    "documents": document_service_stack.service_construct.service,
    "notifications": notification_service_stack.service_construct.service,
    "auth": auth_service_stack.service_construct.service,
    "rules": rules_service_stack.service_construct.service,
    "analytics": analytics_service_stack.service_construct.service,
}

api_gateway_stack = ApiGatewayStack(
    app,
    f"{project}-api-gateway",
    config=CONFIG,
    vpc=network_stack.vpc,
    ecs_security_group=network_stack.ecs_security_group,
    service_targets=service_targets,
    log_group=monitoring_stack.api_gateway_log_group,
    frontend_distribution_domain=storage_stack.frontend_distribution.distribution_domain_name,
    env=env,
)

# Phase 6: Frontend
# config_api_url is a PLAIN STRING (from the FRONTEND_API_URL env var) used to
# write config.js. It must not be a CDK token, since tokens embedded in asset
# file contents cannot be resolved as cross-stack references. The pipeline
# resolves the API Gateway URL from CloudFormation and passes it in. When unset
# (e.g. first-ever synth), config.js is left empty and the app falls back to its
# build-time/localhost default.
frontend_stack = FrontendStack(
    app,
    f"{project}-frontend",
    config=CONFIG,
    frontend_bucket=storage_stack.frontend_bucket,
    frontend_distribution=storage_stack.frontend_distribution,
    api_url=api_gateway_stack.api.url,
    config_api_url=os.environ.get("FRONTEND_API_URL", ""),
    env=env,
)
frontend_stack.add_dependency(api_gateway_stack)

app.synth()
