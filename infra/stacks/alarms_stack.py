"""Alarms Stack — CloudWatch alarms for the ClaimFlow ECS services.

This stack runs after every service stack so it can consume each FargateService's
CDK-generated ServiceName (which is a CloudFormation token at synth time) via
the metric dimensions_map. Every alarm here is subscribed to the shared SNS
topic created in MonitoringStack, which in turn fans out to the DevOps Agent
webhook Lambda.

Per service (7 services), three alarms:

  - ClaimFlow-<svc>-HighCPU          — AWS/ECS CPUUtilization > 70% for 1 minute
  - ClaimFlow-<svc>-HighMemory       — AWS/ECS MemoryUtilization > 80% for 1 minute
  - ClaimFlow-<svc>-NoRunningTasks   — ECS/ContainerInsights RunningTaskCount < 1
                                       for 1 minute

Total: 21 alarms. Every alarm has an AlarmDescription so the DevOps Agent
receives context in the SNS payload.
"""

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_ecs as ecs,
    aws_sns as sns,
    CfnOutput,
)
from constructs import Construct


class AlarmsStack(Stack):
    """Per-service ECS alarms wired to the shared SNS topic."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: dict,
        alarm_topic: sns.ITopic,
        services: dict[str, ecs.FargateService],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster_name = f"{config['project_name']}-cluster"
        cpu_threshold = config.get("monitoring", {}).get("ecs_cpu_alarm_threshold", 70)
        mem_threshold = config.get("monitoring", {}).get("ecs_memory_alarm_threshold", 80)

        self.alarms: list[cw.IAlarm] = []

        for short_name, service in services.items():
            cap = short_name.replace("-", " ").title().replace(" ", "")

            # AWS/ECS metrics use ClusterName + ServiceName dimensions.
            # service.service_name is a CDK token that resolves to the
            # CDK-auto-suffixed service name at deploy time.
            ecs_dims = {
                "ClusterName": cluster_name,
                "ServiceName": service.service_name,
            }
            # ContainerInsights uses the same dimension names.
            ci_dims = dict(ecs_dims)

            # -----------------------------------------
            # High CPU
            # -----------------------------------------
            cpu_alarm = cw.Alarm(
                self,
                f"{cap}CpuAlarm",
                alarm_name=f"ClaimFlow-{short_name}-HighCPU",
                alarm_description=f"{short_name} CPU utilisation above {cpu_threshold}% for 1 minute",
                metric=cw.Metric(
                    namespace="AWS/ECS",
                    metric_name="CPUUtilization",
                    dimensions_map=ecs_dims,
                    statistic="Average",
                    period=Duration.minutes(1),
                ),
                threshold=cpu_threshold,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            cpu_alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            self.alarms.append(cpu_alarm)

            # -----------------------------------------
            # High Memory
            # -----------------------------------------
            mem_alarm = cw.Alarm(
                self,
                f"{cap}MemAlarm",
                alarm_name=f"ClaimFlow-{short_name}-HighMemory",
                alarm_description=f"{short_name} memory utilisation above {mem_threshold}% for 1 minute",
                metric=cw.Metric(
                    namespace="AWS/ECS",
                    metric_name="MemoryUtilization",
                    dimensions_map=ecs_dims,
                    statistic="Average",
                    period=Duration.minutes(1),
                ),
                threshold=mem_threshold,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            mem_alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            self.alarms.append(mem_alarm)

            # -----------------------------------------
            # No Running Tasks
            # -----------------------------------------
            no_tasks_alarm = cw.Alarm(
                self,
                f"{cap}NoTasksAlarm",
                alarm_name=f"ClaimFlow-{short_name}-NoRunningTasks",
                alarm_description=f"{short_name} has zero running tasks (crash loop or all tasks stopped)",
                metric=cw.Metric(
                    namespace="ECS/ContainerInsights",
                    metric_name="RunningTaskCount",
                    dimensions_map=ci_dims,
                    statistic="Average",
                    period=Duration.minutes(1),
                ),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            )
            no_tasks_alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))
            self.alarms.append(no_tasks_alarm)

        CfnOutput(
            self,
            "AlarmCount",
            value=str(len(self.alarms)),
            description="Total number of CloudWatch alarms wired to the DevOps Agent webhook",
        )
