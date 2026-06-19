"""API Gateway Stack — REST API with VPC Link and path-based routing."""

from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct


class ApiGatewayStack(Stack):
    """API Gateway — single REST API with path-based routing to ECS services."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        vpc: ec2.Vpc,
        ecs_security_group: ec2.SecurityGroup,
        service_targets: dict,
        log_group: logs.LogGroup,
        frontend_distribution_domain: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api_config = config["api_gateway"]

        # Network Load Balancer for VPC Link
        self.nlb = elbv2.NetworkLoadBalancer(
            self,
            "NLB",
            vpc=vpc,
            internet_facing=False,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # Create target groups and listeners for each service. Each service gets
        # its own NLB listener on a distinct port; the integration for that
        # route must target the same port.
        self.target_groups = {}
        self.service_ports = {}
        port = 8000
        for service_name, ecs_service in service_targets.items():
            listener = self.nlb.add_listener(
                f"Listener-{service_name}",
                port=port,
                protocol=elbv2.Protocol.TCP,
            )
            target_group = listener.add_targets(
                f"Target-{service_name}",
                port=8000,
                targets=[ecs_service.load_balancer_target(container_name="Container", container_port=8000)],
                health_check=elbv2.HealthCheck(
                    path="/health",
                    protocol=elbv2.Protocol.HTTP,
                ),
            )
            self.target_groups[service_name] = target_group
            self.service_ports[service_name] = port
            port += 1

        # VPC Link
        vpc_link = apigw.VpcLink(
            self,
            "VpcLink",
            targets=[self.nlb],
            description="VPC Link to ECS services",
        )

        # REST API
        self.api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"{config['project_name']}-api",
            description="Claim Processing Services API",
            deploy_options=apigw.StageOptions(
                stage_name=api_config["stage_name"],
                logging_level=apigw.MethodLoggingLevel.INFO,
                access_log_destination=apigw.LogGroupLogDestination(log_group),
                tracing_enabled=True,
                throttling_rate_limit=api_config["throttle_rate_limit"],
                throttling_burst_limit=api_config["throttle_burst_limit"],
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=[f"https://{frontend_distribution_domain}"],
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
                allow_credentials=True,
            ),
        )

        # API resources and integrations
        api_resource = self.api.root.add_resource("api")

        service_routes = [
            "claims",
            "fraud",
            "documents",
            "notifications",
            "auth",
            "rules",
            "analytics",
        ]

        for route in service_routes:
            resource = api_resource.add_resource(route)
            proxy = resource.add_resource("{proxy+}")
            # Route to the NLB listener port assigned to this service.
            service_port = self.service_ports[route]

            # Proxy for sub-paths: /api/<route>/<anything>  ->  service /api/<route>/<anything>
            proxy_integration = apigw.Integration(
                type=apigw.IntegrationType.HTTP_PROXY,
                integration_http_method="ANY",
                uri=f"http://{self.nlb.load_balancer_dns_name}:{service_port}/api/{route}/{{proxy}}",
                options=apigw.IntegrationOptions(
                    connection_type=apigw.ConnectionType.VPC_LINK,
                    vpc_link=vpc_link,
                    request_parameters={
                        "integration.request.path.proxy": "method.request.path.proxy",
                    },
                ),
            )
            proxy.add_method(
                "ANY",
                proxy_integration,
                request_parameters={"method.request.path.proxy": True},
            )

            # Method on the bare resource: /api/<route>  ->  service /api/<route>
            # The frontend calls these for list/create (e.g. GET/POST /api/claims),
            # which the {proxy+} method does not match (it requires a sub-path).
            root_integration = apigw.Integration(
                type=apigw.IntegrationType.HTTP_PROXY,
                integration_http_method="ANY",
                uri=f"http://{self.nlb.load_balancer_dns_name}:{service_port}/api/{route}",
                options=apigw.IntegrationOptions(
                    connection_type=apigw.ConnectionType.VPC_LINK,
                    vpc_link=vpc_link,
                ),
            )
            resource.add_method("ANY", root_integration)

        # Output API URL
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
        )
