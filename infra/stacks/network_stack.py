"""Network Stack — VPC, subnets, NAT Gateway, security groups, VPC endpoints."""

from aws_cdk import Stack, aws_ec2 as ec2, aws_ecs as ecs, aws_servicediscovery as sd
from constructs import Construct


class NetworkStack(Stack):
    """Foundation networking infrastructure."""

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_config = config["vpc"]

        # VPC with public and private subnets
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=f"{config['project_name']}-vpc",
            ip_addresses=ec2.IpAddresses.cidr(vpc_config["cidr"]),
            max_azs=vpc_config["max_azs"],
            nat_gateways=vpc_config["nat_gateways"],
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # VPC Endpoints (Gateway — free)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )
        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )

        # VPC Endpoints (Interface)
        self.vpc.add_interface_endpoint(
            "EcrEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
        )
        self.vpc.add_interface_endpoint(
            "EcrDockerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
        )
        self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
        )

        # Security Groups
        # NOTE: The public entry point is API Gateway backed by an internal
        # (non-internet-facing) Network Load Balancer, so there is no public
        # ALB. ECS tasks only accept traffic from the VPC Link / NLB and from
        # each other on the service port.
        self.ecs_security_group = ec2.SecurityGroup(
            self,
            "EcsSg",
            vpc=self.vpc,
            description="Security group for ECS tasks",
            allow_all_outbound=True,
        )
        # Allow traffic from within the VPC (API Gateway VPC Link / internal NLB
        # resolve to in-VPC addresses) on the service port.
        self.ecs_security_group.add_ingress_rule(
            ec2.Peer.ipv4(vpc_config["cidr"]),
            ec2.Port.tcp(8000),
            "Allow traffic from within the VPC (VPC Link / internal NLB)",
        )
        # Allow ECS tasks to communicate with each other (service-to-service)
        self.ecs_security_group.add_ingress_rule(
            self.ecs_security_group,
            ec2.Port.tcp(8000),
            "Allow inter-service communication",
        )

        self.database_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSg",
            vpc=self.vpc,
            description="Security group for Aurora database",
            allow_all_outbound=False,
        )
        self.database_security_group.add_ingress_rule(
            self.ecs_security_group,
            ec2.Port.tcp(5432),
            "Allow PostgreSQL from ECS tasks",
        )

        # ECS Cluster (shared across all services)
        self.ecs_cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=f"{config['project_name']}-cluster",
            vpc=self.vpc,
            container_insights=True,
        )

        # Cloud Map namespace for service discovery
        self.cloud_map_namespace = sd.PrivateDnsNamespace(
            self,
            "ServiceDiscovery",
            name=config["service_discovery"]["namespace"],
            vpc=self.vpc,
            description="Service discovery namespace for claim processing services",
        )
