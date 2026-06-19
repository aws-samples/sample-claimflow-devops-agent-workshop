"""Reusable ECS Fargate service construct."""

import os

from constructs import Construct
from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_logs as logs,
    aws_servicediscovery as sd,
    Duration,
)


def _container_image(scope: Construct, service_name: str, docker_image_path: str) -> ecs.ContainerImage:
    """Choose the container image source.

    Default (local `./deploy.sh` and the workshop's CodeBuild, which both have a
    Docker daemon): build the image from the service Dockerfile via `from_asset`.

    Opt-in (set only by the GitLab CI pipeline, whose restricted runners cannot
    run a Docker daemon): consume a pre-built image already pushed to ECR by an
    earlier kaniko build stage. Activated with:
        USE_PREBUILT_IMAGES=true
        IMAGE_TAG=<tag>            (e.g. the commit SHA)
        ECR_REGISTRY=<acct>.dkr.ecr.<region>.amazonaws.com  (optional; only the repo name is needed)
    The ECR repository is named "<project>/<service_name>".
    """
    if os.environ.get("USE_PREBUILT_IMAGES", "").lower() == "true":
        image_tag = os.environ.get("IMAGE_TAG", "latest")
        repo_name = f"claim-processing/{service_name}"
        repo = ecr.Repository.from_repository_name(
            scope, "EcrRepo", repository_name=repo_name
        )
        return ecs.ContainerImage.from_ecr_repository(repo, tag=image_tag)
    return ecs.ContainerImage.from_asset(docker_image_path)


class FargateServiceConstruct(Construct):
    """Common ECS Fargate service pattern for all backend microservices."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: ecs.Cluster,
        service_name: str,
        docker_image_path: str,
        vpc: ec2.Vpc,
        security_group: ec2.SecurityGroup,
        cloud_map_namespace: sd.PrivateDnsNamespace,
        log_group: logs.LogGroup,
        cpu: int = 512,
        memory_limit_mib: int = 1024,
        desired_count: int = 1,
        min_capacity: int = 1,
        max_capacity: int = 3,
        cpu_scaling_target: int = 70,
        environment: dict = None,
        secrets: dict = None,
        container_port: int = 8000,
    ) -> None:
        super().__init__(scope, construct_id)

        self.task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description=f"Task role for {service_name}",
        )

        execution_role = iam.Role(
            self,
            "ExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )

        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=cpu,
            memory_limit_mib=memory_limit_mib,
            task_role=self.task_role,
            execution_role=execution_role,
        )

        env_vars = {
            "SERVICE_NAME": service_name,
            "ENVIRONMENT": "dev",
            "LOG_LEVEL": "INFO",
            "PORT": str(container_port),
        }
        if environment:
            env_vars.update(environment)

        self.container = self.task_definition.add_container(
            "Container",
            image=_container_image(self, service_name, docker_image_path),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=service_name,
                log_group=log_group,
            ),
            environment=env_vars,
            secrets=secrets or None,
        )

        self.container.add_port_mappings(
            ecs.PortMapping(container_port=container_port, protocol=ecs.Protocol.TCP)
        )

        self.service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=self.task_definition,
            desired_count=desired_count,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            cloud_map_options=ecs.CloudMapOptions(
                cloud_map_namespace=cloud_map_namespace,
                name=service_name,
            ),
            enable_execute_command=True,
        )

        scaling = self.service.auto_scale_task_count(
            min_capacity=min_capacity,
            max_capacity=max_capacity,
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=cpu_scaling_target,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )
