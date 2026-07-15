#!/usr/bin/env python3
"""
Fault Injection — Scenario 3: DDoS Attack (Extra ECS Tasks Flooding HTTP Requests)

Simulates a volumetric DDoS attack on the claims portal by launching attacker
ECS tasks within the same VPC that flood the ALB with HTTP requests. This
demonstrates how the DevOps Agent detects abnormal traffic patterns and
correlates them with service degradation.

Implementation: Launches standalone Fargate tasks that send continuous HTTP
requests to the claim-service ALB endpoint, causing elevated request counts,
high CPU, increased latency, and potential 5xx errors.

Usage:
    python inject_ddos.py --profile <aws-profile>
    python inject_ddos.py --profile <aws-profile> --attackers 3 --duration 300
"""

import argparse
import boto3
import json
import os
import tempfile
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
        "ec2": session.client("ec2"),
        "logs": session.client("logs"),
    }


def find_cluster_vpc(ecs_client, ec2_client, cluster: str) -> dict:
    """Find the VPC and subnets used by the ECS cluster services."""
    # List services to find network config
    services = ecs_client.list_services(cluster=cluster)["serviceArns"]
    if not services:
        raise RuntimeError(f"No services found in cluster '{cluster}'")

    # Get the first service to find its network configuration
    service_desc = ecs_client.describe_services(cluster=cluster, services=[services[0]])
    service = service_desc["services"][0]

    # Get network config from a running task
    tasks = ecs_client.list_tasks(cluster=cluster, serviceName=services[0], desiredStatus="RUNNING")
    if not tasks.get("taskArns"):
        raise RuntimeError("No running tasks found to determine VPC configuration")

    task_desc = ecs_client.describe_tasks(cluster=cluster, tasks=[tasks["taskArns"][0]])
    attachments = task_desc["tasks"][0].get("attachments", [])

    subnets = []
    security_groups = []
    for attachment in attachments:
        for detail in attachment.get("details", []):
            if detail["name"] == "subnetId":
                subnets.append(detail["value"])
            if detail["name"] == "networkInterfaceId":
                # Get security group from ENI
                eni = ec2_client.describe_network_interfaces(
                    NetworkInterfaceIds=[detail["value"]]
                )["NetworkInterfaces"][0]
                security_groups = [g["GroupId"] for g in eni.get("Groups", [])]

    return {
        "subnets": subnets,
        "security_groups": security_groups,
    }


def get_alb_dns(profile: str, region: str = "us-east-1") -> str:
    """Find the ALB DNS name for the claim processing application."""
    session = boto3.Session(profile_name=profile, region_name=region)
    elb_client = session.client("elbv2")

    paginator = elb_client.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for lb in page["LoadBalancers"]:
            if "claim-processing" in lb.get("LoadBalancerName", ""):
                return lb["DNSName"]

    # Fallback: use service discovery
    return "claim-service.claim-processing.local"


def inject_ddos(
    profile: str,
    cluster: str = "claim-processing-cluster",
    region: str = "us-east-1",
    num_attackers: int = 3,
    duration: int = 300,
):
    """
    Launch attacker ECS tasks that flood the claim-service with HTTP requests.
    """
    clients = get_clients(profile, region)
    ecs_client = clients["ecs"]
    ec2_client = clients["ec2"]

    print("=" * 60)
    print("  FAULT INJECTION — Scenario 3: DDoS Attack (HTTP Flood)")
    print("=" * 60)
    print()

    # Find VPC configuration from existing services
    print("[1/5] Discovering VPC configuration...")
    vpc_config = find_cluster_vpc(ecs_client, ec2_client, cluster)
    print(f"  ✓ Subnets: {vpc_config['subnets']}")
    print(f"  ✓ Security Groups: {vpc_config['security_groups']}")

    # Find the target ALB or service discovery endpoint
    print("[2/5] Finding target endpoint...")
    target_url = f"http://claim-service.claim-processing.local:8000"
    print(f"  ✓ Target: {target_url}")

    # Ensure log group exists for attacker tasks
    print("[3/5] Setting up attacker log group...")
    logs_client = clients["logs"]
    log_group_name = "/claim-processing/ddos-attacker"
    try:
        logs_client.create_log_group(logGroupName=log_group_name)
        print(f"  ✓ Created log group: {log_group_name}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"  ✓ Log group exists: {log_group_name}")

    # Register attacker task definition
    print("[4/5] Registering attacker task definition...")

    # The attacker script floods multiple endpoints with varying request patterns.
    # Uses a multi-line source string so `while`/`try` compound statements parse
    # correctly — a semicolon-joined one-liner is a SyntaxError.
    attack_script = (
        "import urllib.request, time, random, os, sys\n"
        "sys.stdout.write(f'[ATTACKER] DDoS flood started (PID {os.getpid()})\\n')\n"
        "sys.stdout.flush()\n"
        f"target = '{target_url}'\n"
        "endpoints = ['/api/claims', '/api/claims?status=pending', '/api/claims?page=1&size=100', '/health']\n"
        f"end_time = time.time() + {duration}\n"
        "count = 0\n"
        "errors = 0\n"
        "while time.time() < end_time:\n"
        "    try:\n"
        "        ep = random.choice(endpoints)\n"
        "        url = f'{target}{ep}'\n"
        "        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'X-Forwarded-For': f'10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}'})\n"
        "        urllib.request.urlopen(req, timeout=5)\n"
        "        count += 1\n"
        "    except Exception as e:\n"
        "        errors += 1\n"
        "    if count % 100 == 0:\n"
        "        sys.stdout.write(f'[ATTACKER] Sent {count} requests ({errors} errors)\\n')\n"
        "        sys.stdout.flush()\n"
        "    time.sleep(random.uniform(0.01, 0.05))\n"
        "sys.stdout.write(f'[ATTACKER] Flood complete: {count} requests, {errors} errors\\n')\n"
        "sys.stdout.flush()\n"
    )

    # Get execution role from an existing task
    services = ecs_client.list_services(cluster=cluster)["serviceArns"]
    service_desc = ecs_client.describe_services(cluster=cluster, services=[services[0]])
    existing_task_def_arn = service_desc["services"][0]["taskDefinition"]
    existing_task_def = ecs_client.describe_task_definition(taskDefinition=existing_task_def_arn)["taskDefinition"]
    execution_role_arn = existing_task_def["executionRoleArn"]

    task_def_resp = ecs_client.register_task_definition(
        family="ddos-attacker",
        networkMode="awsvpc",
        requiresCompatibilities=["FARGATE"],
        cpu="256",
        memory="512",
        executionRoleArn=execution_role_arn,
        containerDefinitions=[
            {
                "name": "attacker",
                "image": "python:3.12-slim",
                "essential": True,
                "command": ["python3", "-c", attack_script],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": log_group_name,
                        "awslogs-region": region,
                        "awslogs-stream-prefix": "attacker",
                    },
                },
            }
        ],
    )
    task_def_arn = task_def_resp["taskDefinition"]["taskDefinitionArn"]
    print(f"  ✓ Registered: {task_def_arn.split('/')[-1]}")

    # Launch attacker tasks
    print(f"[5/5] Launching {num_attackers} attacker tasks...")
    launched_tasks = []
    for i in range(num_attackers):
        resp = ecs_client.run_task(
            cluster=cluster,
            taskDefinition=task_def_arn,
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": vpc_config["subnets"][:2],
                    "securityGroups": vpc_config["security_groups"],
                    "assignPublicIp": "DISABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": "attacker",
                        "environment": [
                            {"name": "ATTACKER_ID", "value": str(i + 1)},
                        ],
                    }
                ]
            },
        )
        if resp.get("tasks"):
            task_arn = resp["tasks"][0]["taskArn"]
            launched_tasks.append(task_arn)
            print(f"  ✓ Attacker {i + 1} launched: {task_arn.split('/')[-1]}")
        else:
            print(f"  ✗ Attacker {i + 1} failed to launch")
            if resp.get("failures"):
                print(f"    Reason: {resp['failures'][0].get('reason', 'unknown')}")

    print()
    print(f"  ✓ {len(launched_tasks)}/{num_attackers} attacker tasks running")
    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  SCENARIO 3 ACTIVE: DDoS Attack (HTTP Flood)            │")
    print("  │                                                         │")
    print("  │  What's happening:                                      │")
    print(f"  │  • {len(launched_tasks)} attacker tasks flooding claim-service        │")
    print(f"  │  • Each sends ~20-100 requests/second                   │")
    print(f"  │  • Attack duration: {duration} seconds ({duration // 60} minutes)              │")
    print("  │  • Multiple endpoints targeted (/api/claims/*)          │")
    print("  │  • Spoofed X-Forwarded-For headers (varied IPs)         │")
    print("  │                                                         │")
    print("  │  Expected DevOps Agent detection:                       │")
    print("  │  • Sudden spike in request count on ALB                 │")
    print("  │  • Elevated CPU across claim-service tasks              │")
    print("  │  • Increased API latency (p95 > 2s)                     │")
    print("  │  • Possible 5xx errors as service gets overwhelmed      │")
    print("  │  • Abnormal traffic pattern from internal IPs           │")
    print("  │  • New 'ddos-attacker' tasks visible in ECS cluster     │")
    print("  │                                                         │")
    print("  │  Attack tasks will self-terminate after duration.        │")
    print("  │  Use recover_all.py to stop immediately if needed.      │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # Save task ARNs for recovery. Use the platform temp directory rather than a
    # hardcoded /tmp path so this works cross-platform; recover_all.py reads the
    # same location.
    state_file = os.path.join(tempfile.gettempdir(), "ddos-attack-tasks.json")
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"task_arns": launched_tasks, "cluster": cluster, "log_group": log_group_name}, f)
    print(f"  State saved to {state_file} (used by recover_all.py)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject Scenario 3: DDoS Attack fault")
    parser.add_argument("--profile", default=None, help="AWS profile name (omit to use ambient credentials, e.g. in CloudShell)")
    parser.add_argument("--cluster", default="claim-processing-cluster", help="ECS cluster name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--attackers", type=int, default=3, help="Number of attacker tasks to launch")
    parser.add_argument("--duration", type=int, default=300, help="Attack duration in seconds")
    args = parser.parse_args()

    inject_ddos(args.profile, args.cluster, args.region, args.attackers, args.duration)
