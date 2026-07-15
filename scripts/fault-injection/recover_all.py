#!/usr/bin/env python3
"""
Recovery Script — Restore All Services to Healthy State

Reverses all three fault injection scenarios:
  1. Bad Query (High CPU) — Removes bad-query-simulator sidecar from claim-service
  2. Memory Sidecar (OOM) — Removes ml-model-loader sidecar from fraud-service
  3. DDoS Attack — Stops all attacker tasks and cleans up task definitions

Usage:
    python recover_all.py --profile <aws-profile>
    python recover_all.py --profile <aws-profile> --verify-only
"""

import argparse
import boto3
import json
import sys
import os
import tempfile


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


def find_service(ecs_client, cluster: str, service_keyword: str) -> str | None:
    """Find an ECS service ARN by keyword."""
    paginator = ecs_client.get_paginator("list_services")
    for page in paginator.paginate(cluster=cluster):
        for arn in page["serviceArns"]:
            if service_keyword in arn:
                return arn
    return None


def get_original_task_def(ecs_client, family: str) -> str | None:
    """
    Find the original (clean) task definition for a service by looking for
    one without injected sidecar containers.
    """
    resp = ecs_client.list_task_definitions(familyPrefix=family, sort="DESC", status="ACTIVE")
    for task_def_arn in resp.get("taskDefinitionArns", []):
        td = ecs_client.describe_task_definition(taskDefinition=task_def_arn)["taskDefinition"]
        container_names = [c["name"] for c in td["containerDefinitions"]]
        # Original task def only has "Container" (the main app container)
        injected_names = {"bad-query-simulator", "ml-model-loader"}
        if not injected_names.intersection(set(container_names)):
            return task_def_arn
    return None


def recover_service(ecs_client, cluster: str, service_keyword: str, service_label: str) -> bool:
    """Recover a single service by reverting to its clean task definition."""
    service_arn = find_service(ecs_client, cluster, service_keyword)
    if not service_arn:
        print(f"  ⚠ {service_label} not found — skipping")
        return False

    # Get current task def
    service_desc = ecs_client.describe_services(cluster=cluster, services=[service_arn])
    current_task_def = service_desc["services"][0]["taskDefinition"]
    current_td = ecs_client.describe_task_definition(taskDefinition=current_task_def)["taskDefinition"]

    container_names = [c["name"] for c in current_td["containerDefinitions"]]
    injected_names = {"bad-query-simulator", "ml-model-loader"}

    if not injected_names.intersection(set(container_names)):
        print(f"  ✓ {service_label} — already clean (no injected sidecars)")
        return True

    # Find the original clean task definition
    family = current_td["family"]
    original_td_arn = get_original_task_def(ecs_client, family)

    if not original_td_arn:
        # If we can't find a clean one, create one by removing sidecars
        print(f"  ⚠ No clean task definition found for {family} — creating one...")
        clean_containers = [c for c in current_td["containerDefinitions"] if c["name"] not in injected_names]
        new_td = ecs_client.register_task_definition(
            family=family,
            taskRoleArn=current_td["taskRoleArn"],
            executionRoleArn=current_td["executionRoleArn"],
            networkMode=current_td["networkMode"],
            containerDefinitions=clean_containers,
            requiresCompatibilities=current_td["requiresCompatibilities"],
            cpu=current_td["cpu"],
            memory=current_td["memory"],
        )
        original_td_arn = new_td["taskDefinition"]["taskDefinitionArn"]
        print(f"  ✓ Created clean task definition: {original_td_arn.split('/')[-1]}")
    else:
        print(f"  ✓ Found clean task definition: {original_td_arn.split('/')[-1]}")

    # Update service to use clean task definition. Restore default deployment
    # config (100/200, circuit breaker enabled) so the service behaves normally
    # again — inject_memory_sidecar.py had set minimumHealthyPercent=0 to force
    # the crash loop.
    service_name = service_arn.split("/")[-1]
    ecs_client.update_service(
        cluster=cluster,
        service=service_name,
        taskDefinition=original_td_arn,
        forceNewDeployment=True,
        deploymentConfiguration={
            "minimumHealthyPercent": 100,
            "maximumPercent": 200,
            "deploymentCircuitBreaker": {"enable": True, "rollback": True},
        },
    )
    print(f"  ✓ {service_label} — reverted to clean task definition")
    return True


def stop_ddos_tasks(ecs_client, cluster: str) -> int:
    """Stop all running DDoS attacker tasks."""
    stopped_count = 0

    # Read tasks from the state file written by inject_ddos.py (same location).
    state_file = os.path.join(tempfile.gettempdir(), "ddos-attack-tasks.json")
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        for task_arn in state.get("task_arns", []):
            try:
                ecs_client.stop_task(cluster=cluster, task=task_arn, reason="Recovery: stopping DDoS attacker")
                stopped_count += 1
            except Exception as e:
                print(f"  (skip) could not stop {task_arn}: {e}")
        os.remove(state_file)

    # Also scan for any running ddos-attacker tasks
    try:
        resp = ecs_client.list_tasks(cluster=cluster, family="ddos-attacker", desiredStatus="RUNNING")
        for task_arn in resp.get("taskArns", []):
            try:
                ecs_client.stop_task(cluster=cluster, task=task_arn, reason="Recovery: stopping DDoS attacker")
                stopped_count += 1
            except Exception as e:
                print(f"  (skip) could not stop {task_arn}: {e}")
    except Exception as e:
        print(f"  (skip) could not list RUNNING attacker tasks: {e}")

    # Also check for PENDING tasks
    try:
        resp = ecs_client.list_tasks(cluster=cluster, family="ddos-attacker", desiredStatus="PENDING")
        for task_arn in resp.get("taskArns", []):
            try:
                ecs_client.stop_task(cluster=cluster, task=task_arn, reason="Recovery: stopping DDoS attacker")
                stopped_count += 1
            except Exception as e:
                print(f"  (skip) could not stop {task_arn}: {e}")
    except Exception as e:
        print(f"  (skip) could not list PENDING attacker tasks: {e}")

    return stopped_count


def cleanup_ddos_task_definitions(ecs_client):
    """Deregister DDoS attacker task definitions."""
    deregistered = 0
    try:
        resp = ecs_client.list_task_definitions(familyPrefix="ddos-attacker", status="ACTIVE")
        for td_arn in resp.get("taskDefinitionArns", []):
            ecs_client.deregister_task_definition(taskDefinition=td_arn)
            deregistered += 1
    except Exception as e:
        print(f"  (skip) could not deregister attacker task definitions: {e}")
    return deregistered


def cleanup_log_group(logs_client, log_group_name: str):
    """Delete the DDoS attacker log group."""
    try:
        logs_client.delete_log_group(logGroupName=log_group_name)
        return True
    except Exception:
        return False


def verify_services(ecs_client, cluster: str) -> dict:
    """Verify all services are healthy."""
    results = {}
    services_resp = ecs_client.list_services(cluster=cluster)
    if not services_resp["serviceArns"]:
        return results

    desc = ecs_client.describe_services(cluster=cluster, services=services_resp["serviceArns"])
    for svc in desc["services"]:
        name = svc["serviceName"]
        running = svc["runningCount"]
        desired = svc["desiredCount"]
        status = "✓ Healthy" if running >= desired and running > 0 else f"✗ Unhealthy ({running}/{desired})"
        results[name] = {"running": running, "desired": desired, "status": status}

    return results


def recover_all(
    profile: str,
    cluster: str = "claim-processing-cluster",
    region: str = "us-east-1",
    verify_only: bool = False,
):
    """Execute full recovery across all fault injection scenarios."""
    clients = get_clients(profile, region)
    ecs_client = clients["ecs"]
    logs_client = clients["logs"]

    print("=" * 60)
    print("  RECOVERY — Restoring All Services to Healthy State")
    print("=" * 60)
    print()

    if verify_only:
        print("[Verify Mode] Checking service health only...")
        print()
        results = verify_services(ecs_client, cluster)
        print("  Service Health:")
        for name, info in sorted(results.items()):
            print(f"    {info['status']}  {name} ({info['running']}/{info['desired']} tasks)")
        print()
        return

    # Step 1: Stop DDoS attacker tasks
    print("[1/5] Stopping DDoS attacker tasks...")
    stopped = stop_ddos_tasks(ecs_client, cluster)
    if stopped > 0:
        print(f"  ✓ Stopped {stopped} attacker task(s)")
    else:
        print("  ✓ No active attacker tasks found")

    # Step 2: Cleanup DDoS task definitions
    print("[2/5] Cleaning up DDoS task definitions...")
    deregistered = cleanup_ddos_task_definitions(ecs_client)
    if deregistered > 0:
        print(f"  ✓ Deregistered {deregistered} attacker task definition(s)")
    else:
        print("  ✓ No attacker task definitions to clean up")

    # Step 3: Recover claim-service (Scenario 1 — Bad Query)
    print("[3/5] Recovering claim-service (Scenario 1: Bad Query)...")
    recover_service(ecs_client, cluster, "claim-service", "claim-service")

    # Step 4: Recover fraud-service (Scenario 2 — Memory Sidecar)
    print("[4/5] Recovering fraud-service (Scenario 2: Memory Sidecar)...")
    recover_service(ecs_client, cluster, "fraud-service", "fraud-service")

    # Step 5: Cleanup DDoS log group
    print("[5/5] Cleaning up attacker log group...")
    if cleanup_log_group(logs_client, "/claim-processing/ddos-attacker"):
        print("  ✓ Deleted /claim-processing/ddos-attacker log group")
    else:
        print("  ✓ No attacker log group to clean up")

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  RECOVERY COMPLETE                                      │")
    print("  │                                                         │")
    print("  │  Actions taken:                                         │")
    print("  │  • Stopped all DDoS attacker tasks                      │")
    print("  │  • Reverted claim-service to clean task definition      │")
    print("  │  • Reverted fraud-service to clean task definition      │")
    print("  │  • Cleaned up attacker task definitions & log groups    │")
    print("  │                                                         │")
    print("  │  Services are redeploying with clean configurations.    │")
    print("  │  Allow 60-90 seconds for full stabilization.            │")
    print("  │                                                         │")
    print("  │  Verify with: python recover_all.py --verify-only       │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # Wait for the ECS service deployments to actually stabilize, rather than
    # pausing for a fixed time. The waiter returns as soon as every service
    # reaches a steady state (or raises if it does not within the limit).
    print("Waiting for services to stabilize...")
    service_arns = ecs_client.list_services(cluster=cluster).get("serviceArns", [])
    if service_arns:
        waiter = ecs_client.get_waiter("services_stable")
        try:
            waiter.wait(
                cluster=cluster,
                services=service_arns,
                WaiterConfig={"Delay": 15, "MaxAttempts": 12},
            )
        except Exception as e:
            print(f"  Services did not fully stabilize in time: {e}")
    print()
    print("Service Health Check:")
    results = verify_services(ecs_client, cluster)
    for name, info in sorted(results.items()):
        print(f"  {info['status']}  {name} ({info['running']}/{info['desired']} tasks)")
    print()
    print("Note: If services show unhealthy, wait another 60s for deployments to complete.")
    print("Run: python recover_all.py --profile <profile> --verify-only")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recover all services from fault injections")
    parser.add_argument("--profile", default=None, help="AWS profile name (omit to use ambient credentials, e.g. in CloudShell)")
    parser.add_argument("--cluster", default="claim-processing-cluster", help="ECS cluster name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--verify-only", action="store_true", help="Only verify service health, don't recover")
    args = parser.parse_args()

    recover_all(args.profile, args.cluster, args.region, args.verify_only)
