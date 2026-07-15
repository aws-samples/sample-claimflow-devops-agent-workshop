#!/usr/bin/env python3
"""
Fault Injection — Scenario 1: Bad Query (INNER JOIN causing High CPU)

Simulates a poorly optimized database query in the claim-service that causes
sustained high CPU utilization. This mimics a real production issue where a
developer deploys a query with an expensive INNER JOIN across policy tables,
claim history, and adjudication records.

Implementation: Adds a CPU-burning sidecar container ('bad-query-simulator')
to the claim-service task definition using the ECS API, then redeploys the
service. The sidecar drives sustained high CPU on the task.

Usage:
    python inject_bad_query.py --profile <aws-profile>
"""

import argparse
import boto3
import sys


def get_clients(profile: str = None, region: str = "us-east-1"):
    """Create boto3 clients.

    If a profile name is provided, use it. Otherwise fall back to the ambient
    credentials in the environment (for example, an AWS CloudShell session or an
    attached instance/role), which is how the workshop runs the scripts.
    """
    if profile and profile != "default":
        session = boto3.Session(profile_name=profile, region_name=region)
    else:
        session = boto3.Session(region_name=region)
    return {
        "ecs": session.client("ecs"),
        "logs": session.client("logs"),
    }


def find_service(ecs_client, cluster: str, service_keyword: str) -> str:
    """Find an ECS service ARN by keyword."""
    paginator = ecs_client.get_paginator("list_services")
    for page in paginator.paginate(cluster=cluster):
        for arn in page["serviceArns"]:
            if service_keyword in arn:
                return arn
    raise RuntimeError(f"Service matching '{service_keyword}' not found in cluster '{cluster}'")


def get_task_arns(ecs_client, cluster: str, service: str) -> list:
    """Get running task ARNs for a service."""
    resp = ecs_client.list_tasks(cluster=cluster, serviceName=service, desiredStatus="RUNNING")
    return resp.get("taskArns", [])


def inject_bad_query(profile: str, cluster: str = "claim-processing-cluster", region: str = "us-east-1"):
    """
    Inject the bad query fault by adding a CPU-burning sidecar container to the
    claim-service task definition. The sidecar simulates an expensive INNER JOIN
    query, driving sustained high CPU on the task.

    This uses the boto3 ECS API only (register task definition + update service);
    it does not shell out to the AWS CLI.
    """
    clients = get_clients(profile, region)
    ecs_client = clients["ecs"]

    print("=" * 60)
    print("  FAULT INJECTION — Scenario 1: Bad Query (High CPU)")
    print("=" * 60)
    print()

    # Find claim-service
    print("[1/3] Finding claim-service...")
    service_arn = find_service(ecs_client, cluster, "claim-service")
    print(f"  ✓ Found: {service_arn.split('/')[-1]}")

    # Confirm the service has running tasks before mutating it
    print("[2/3] Checking running tasks...")
    task_arns = get_task_arns(ecs_client, cluster, service_arn)
    if not task_arns:
        print("  ✗ No running tasks found. Is the service healthy?")
        sys.exit(1)
    print(f"  ✓ Found {len(task_arns)} running task(s)")

    # Add the CPU-burn sidecar via the ECS API
    print("[3/3] Adding 'bad-query-simulator' sidecar...")
    inject_via_update(ecs_client, cluster, service_arn, region)


def inject_via_update(ecs_client, cluster: str, service_arn: str, region: str):
    """
    Register a new claim-service task definition that includes a CPU-burn
    sidecar, then update the service to use it. Uses only the ECS API.
    """
    # Get current task definition
    service_desc = ecs_client.describe_services(cluster=cluster, services=[service_arn])
    task_def_arn = service_desc["services"][0]["taskDefinition"]
    task_def = ecs_client.describe_task_definition(taskDefinition=task_def_arn)["taskDefinition"]

    container_defs = task_def["containerDefinitions"].copy()

    # CPU-burn sidecar: simulates an expensive INNER JOIN query. The command is
    # a fixed constant passed as an argument list to the container runtime.
    # The payload uses exec() with a multi-line string so the `while`/`for`
    # compound statements parse correctly — a semicolon-joined one-liner is a
    # SyntaxError.
    #
    # Uses multiprocessing to spawn N workers that each burn a full CPU core.
    # Fargate publishes CPUUtilization as a percentage of allocated task CPU,
    # so a single-threaded loop only pins ~25-50% of task CPU. Multiple
    # workers push utilisation reliably above the 50% alarm threshold.
    cpu_burn_payload = (
        "import hashlib, time, sys, os\n"
        "from multiprocessing import Process\n"
        "sys.stdout.write('[FAULT] Bad query INNER JOIN simulation started\\n')\n"
        "sys.stdout.flush()\n"
        "def burn():\n"
        "    start = time.time()\n"
        "    while time.time() - start < 600:\n"
        "        for i in range(100000):\n"
        "            hashlib.sha256(str(i).encode()).hexdigest()\n"
        "workers = [Process(target=burn) for _ in range(4)]\n"
        "for w in workers:\n"
        "    w.start()\n"
        "for w in workers:\n"
        "    w.join()\n"
    )
    cpu_burn_container = {
        "name": "bad-query-simulator",
        "image": "python:3.12-slim",
        "essential": False,
        # No explicit cpu/memory cap: on a 512-unit task the sidecar was pinned
        # to ~33% CPU because a hard 256 cap left the main container free to
        # keep running. Letting it inherit the task-level pool means it burns
        # everything the app is not using, which reliably crosses the 60%
        # HighCPU alarm threshold.
        "memory": 256,
        "command": ["python3", "-c", cpu_burn_payload],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": "/claim-processing/claim-service",
                "awslogs-region": region,
                "awslogs-stream-prefix": "bad-query-fault",
            },
        },
    }

    container_defs.append(cpu_burn_container)

    new_task_def = ecs_client.register_task_definition(
        family=task_def["family"],
        taskRoleArn=task_def["taskRoleArn"],
        executionRoleArn=task_def["executionRoleArn"],
        networkMode=task_def["networkMode"],
        containerDefinitions=container_defs,
        requiresCompatibilities=task_def["requiresCompatibilities"],
        cpu=task_def["cpu"],
        memory=task_def["memory"],
    )

    new_task_def_arn = new_task_def["taskDefinition"]["taskDefinitionArn"]
    print(f"  ✓ Registered new task definition: {new_task_def_arn.split('/')[-1]}")

    service_name = service_arn.split("/")[-1]
    ecs_client.update_service(
        cluster=cluster,
        service=service_name,
        taskDefinition=new_task_def_arn,
        forceNewDeployment=True,
    )
    print(f"  ✓ Updated claim-service with bad-query-simulator sidecar")
    print(f"  ✓ New deployment rolling out (takes ~60 seconds)")
    print()
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  SCENARIO 1 ACTIVE: Bad Query (High CPU)            │")
    print("  │                                                     │")
    print("  │  What's happening:                                  │")
    print("  │  • A 'bad-query-simulator' sidecar was added to     │")
    print("  │    the claim-service task definition                 │")
    print("  │  • It simulates an expensive INNER JOIN query        │")
    print("  │  • CPU utilization will spike to 80-100%            │")
    print("  │  • CloudWatch CPU alarm will fire within 3-5 min    │")
    print("  │                                                     │")
    print("  │  Expected DevOps Agent detection:                   │")
    print("  │  • High CPU alarm on claim-service                  │")
    print("  │  • Logs show 'Bad query INNER JOIN simulation'      │")
    print("  │  • API response times degraded on /api/claims/*     │")
    print("  └─────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject Scenario 1: Bad Query fault")
    parser.add_argument("--profile", default=None, help="AWS profile name (omit to use ambient credentials, e.g. in CloudShell)")
    parser.add_argument("--cluster", default="claim-processing-cluster", help="ECS cluster name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    inject_bad_query(args.profile, args.cluster, args.region)
