#!/usr/bin/env python3
"""
Fault Injection — Scenario 2: Memory-Stress Sidecar (OOM Kill)

Simulates a misconfigured sidecar container (e.g., a fraud-detection ML model
or document parsing engine) that exhausts memory and causes the ECS task to be
OOM-killed.

Implementation: Adds a memory-hungry sidecar container to the fraud-service
task definition that allocates memory until the task hits its memory limit
and gets killed by ECS/Linux OOM killer.

Usage:
    python inject_memory_sidecar.py --profile <aws-profile>
"""

import argparse
import boto3
import json
import time
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


def inject_memory_sidecar(
    profile: str,
    cluster: str = "claim-processing-cluster",
    region: str = "us-east-1",
    target_service: str = "fraud-service",
):
    """
    Inject a memory-exhausting sidecar into the fraud-service task definition.
    The sidecar will progressively allocate memory until the ECS task is killed.
    """
    clients = get_clients(profile, region)
    ecs_client = clients["ecs"]

    print("=" * 60)
    print("  FAULT INJECTION — Scenario 2: Memory-Stress Sidecar (OOM)")
    print("=" * 60)
    print()

    # Find target service
    print(f"[1/4] Finding {target_service}...")
    service_arn = find_service(ecs_client, cluster, target_service)
    print(f"  ✓ Found: {service_arn.split('/')[-1]}")

    # Get current task definition
    print("[2/4] Reading current task definition...")
    service_desc = ecs_client.describe_services(cluster=cluster, services=[service_arn])
    task_def_arn = service_desc["services"][0]["taskDefinition"]
    task_def = ecs_client.describe_task_definition(taskDefinition=task_def_arn)["taskDefinition"]
    print(f"  ✓ Current task def: {task_def_arn.split('/')[-1]}")

    # Create new task definition with memory-stress sidecar
    print("[3/4] Adding memory-stress sidecar container...")
    container_defs = task_def["containerDefinitions"].copy()

    # Memory stress sidecar — simulates a misconfigured ML model loader
    # that leaks memory progressively until OOM
    memory_stress_container = {
        "name": "ml-model-loader",
        "image": "python:3.12-slim",
        "essential": True,  # Essential=True means task dies when this container OOMs
        "cpu": 64,
        "memory": 512,  # Give it 512MB — it will try to allocate more
        "command": [
            "python3", "-c",
            (
                "import sys, time, os; "
                "sys.stdout.write(f'[ml-model-loader] Starting fraud detection model load (PID {os.getpid()})\\n'); "
                "sys.stdout.flush(); "
                "# Simulate progressive memory leak from ML model caching\\n"
                "chunks = []; "
                "time.sleep(30); "  # Wait 30s before starting to fill memory (looks realistic)
                "sys.stdout.write('[ml-model-loader] Loading model weights into memory...\\n'); "
                "sys.stdout.flush(); "
                "for i in range(200): "
                "    chunk = b'X' * (5 * 1024 * 1024); "  # Allocate 5MB per iteration
                "    chunks.append(chunk); "
                "    mb = (i + 1) * 5; "
                "    sys.stdout.write(f'[ml-model-loader] Cached {mb}MB of model weights\\n'); "
                "    sys.stdout.flush(); "
                "    time.sleep(2)"  # Gradual — 5MB every 2 seconds
            ),
        ],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": f"/claim-processing/{target_service}",
                "awslogs-region": region,
                "awslogs-stream-prefix": "ml-model-loader",
            },
        },
    }

    container_defs.append(memory_stress_container)

    # Register new task definition
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
    print(f"  ✓ Added 'ml-model-loader' sidecar (essential=true)")

    # Update service to use new task definition
    print("[4/4] Deploying faulty task definition...")
    service_name = service_arn.split("/")[-1]
    ecs_client.update_service(
        cluster=cluster,
        service=service_name,
        taskDefinition=new_task_def_arn,
        forceNewDeployment=True,
    )
    print(f"  ✓ Updated {target_service} with memory-stress sidecar")
    print(f"  ✓ New deployment rolling out...")
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  SCENARIO 2 ACTIVE: Memory-Stress Sidecar (OOM Kill)    │")
    print("  │                                                         │")
    print("  │  What's happening:                                      │")
    print("  │  • An 'ml-model-loader' sidecar was added to            │")
    print("  │    the fraud-service task definition                     │")
    print("  │  • It simulates a misconfigured ML model that leaks     │")
    print("  │    memory (5MB every 2 seconds)                         │")
    print("  │  • After ~30s warmup + ~60-90s of allocation, the       │")
    print("  │    task will be OOM-killed                              │")
    print("  │  • ECS will restart it → OOM again → crash loop         │")
    print("  │                                                         │")
    print("  │  Expected DevOps Agent detection:                       │")
    print("  │  • Task stopped with reason: OutOfMemoryError           │")
    print("  │  • Service shows task cycling (start → crash → restart) │")
    print("  │  • High memory alarm on fraud-service                   │")
    print("  │  • Logs show 'ml-model-loader' allocating memory        │")
    print("  │  • /api/fraud/* requests failing (503 or timeout)       │")
    print("  │                                                         │")
    print("  │  Timeline:                                              │")
    print("  │  • 0-60s: New task deploying                            │")
    print("  │  • 60-90s: Sidecar starts loading 'model weights'       │")
    print("  │  • 90-180s: First OOM kill, task restart                │")
    print("  │  • 180s+: Crash loop established, alarms firing         │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject Scenario 2: Memory-Stress Sidecar fault")
    parser.add_argument("--profile", default=None, help="AWS profile name (omit to use ambient credentials, e.g. in CloudShell)")
    parser.add_argument("--cluster", default="claim-processing-cluster", help="ECS cluster name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--target", default="fraud-service", help="Target service to inject sidecar into")
    args = parser.parse_args()

    inject_memory_sidecar(args.profile, args.cluster, args.region, args.target)
