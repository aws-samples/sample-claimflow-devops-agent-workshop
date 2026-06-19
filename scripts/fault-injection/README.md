# Fault Injection Scripts — DevOps Agent Demo

Three fault injection scenarios demonstrating AWS DevOps Agent capabilities for autonomous incident detection, diagnosis, and remediation.

## Story Arc

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Scenario 1   │     │ Scenario 2   │     │ Scenario 3   │
│ Bad Query    │     │ Memory OOM   │     │ DDoS Attack  │
│ (High CPU)   │     │ (OOM Kill)   │     │ (HTTP Flood) │
│              │     │              │     │              │
│ Data-layer   │     │ Resource     │     │ External     │
│ stress       │     │ exhaustion   │     │ attack       │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
   Inject → Agent → Recover → Inject → Agent → Recover → Inject → Agent → Recover
```

Each scenario is run **one at a time**:
1. Inject the fault
2. Wait for DevOps Agent to detect and investigate
3. Recover the system
4. Move to next scenario

---

## Prerequisites

```bash
pip install boto3
```

AWS profile must have permissions for:
- ECS (describe, update, run-task, stop-task, execute-command, register-task-definition)
- CloudWatch Logs (create/delete log groups)
- EC2 (describe network interfaces)
- ELB (describe load balancers)

---

## Quick Start — Shell Scripts

### Inject a fault
```bash
./inject.sh <scenario> <aws-profile>
```

### Recover (between scenarios or at end)
```bash
./recover.sh <aws-profile>
```

### Verify health
```bash
./recover.sh <aws-profile> --verify-only
```

---

## Demo Flow (Sequential)

### 1. Verify clean state before demo
```bash
./recover.sh my-profile --verify-only
```

### 2. Scenario 1: Bad Query (High CPU)
```bash
./inject.sh 1 my-profile
```
- Wait 3-5 min for CPU alarm to fire
- Show DevOps Agent auto-investigation
- Agent identifies: "claim-service has a bad-query-simulator sidecar burning CPU"

**Recover before next scenario:**
```bash
./recover.sh my-profile
```
Wait 60-90 seconds for services to stabilize.

### 3. Scenario 2: Memory Sidecar (OOM Kill)
```bash
./inject.sh 2 my-profile
```
- Wait 2-3 min for OOM crash loop
- Show DevOps Agent detecting task cycling
- Agent identifies: "ml-model-loader sidecar is exhausting memory"

**Recover before next scenario:**
```bash
./recover.sh my-profile
```
Wait 60-90 seconds for services to stabilize.

### 4. Scenario 3: DDoS Attack (HTTP Flood)
```bash
./inject.sh 3 my-profile
```
- Wait 1-2 min for traffic spike
- Show DevOps Agent correlating traffic patterns
- Agent identifies: "Abnormal traffic from ddos-attacker tasks"

**Final recovery:**
```bash
./recover.sh my-profile
```

### 5. Verify clean state (ready for next demo)
```bash
./recover.sh my-profile --verify-only
```

---

## Scenario Details

### Scenario 1: Bad Query — INNER JOIN Causing High CPU

**What it does**: Adds a CPU-burning sidecar (`bad-query-simulator`) to the claim-service task definition that simulates an expensive INNER JOIN query across policy tables, claim history, and adjudication records.

**Target**: claim-service

**Symptoms**:
- claim-service CPU spikes to 80-100%
- API response times degrade on `/api/claims/*`
- CloudWatch CPU alarm fires within 3-5 minutes

---

### Scenario 2: Memory-Stress Sidecar — OOM Kill

**What it does**: Adds a memory-hungry sidecar (`ml-model-loader`) to the fraud-service that simulates a misconfigured ML model loading process. It progressively allocates memory (5MB every 2 seconds) until the task is OOM-killed.

**Target**: fraud-service

**Symptoms**:
- fraud-service task enters crash loop (start → OOM → restart)
- Task stopped reason: "OutOfMemoryError"
- `/api/fraud/*` requests fail with 503
- High memory alarm fires
- Logs show "ml-model-loader" allocating excessive memory

---

### Scenario 3: DDoS Attack — HTTP Flood via ECS Tasks

**What it does**: Launches standalone Fargate tasks (`ddos-attacker`) within the same VPC that flood the claim-service with HTTP requests (~20-100 req/s per attacker).

**Target**: claim-service (via internal VPC traffic)

**Symptoms**:
- Sudden spike in ALB request count
- Elevated CPU across claim-service tasks
- Increased API latency (p95 > 2s)
- Possible 5xx errors as service gets overwhelmed
- Abnormal traffic patterns from internal IPs
- Unexpected `ddos-attacker` tasks visible in ECS cluster

---

## Recovery

`recover.sh` reverses all faults and restores the system:

1. Stops all DDoS attacker tasks
2. Deregisters attacker task definitions
3. Reverts claim-service to clean task definition (removes `bad-query-simulator`)
4. Reverts fraud-service to clean task definition (removes `ml-model-loader`)
5. Cleans up attacker log groups
6. Verifies all services are healthy

Allow 60-90 seconds after recovery for ECS deployments to stabilize.

---

## CLI Reference

### Shell Scripts (recommended for demos)

| Script | Usage |
|--------|-------|
| `./inject.sh 1 <profile>` | Inject Scenario 1: Bad Query |
| `./inject.sh 2 <profile>` | Inject Scenario 2: Memory OOM |
| `./inject.sh 3 <profile> [--attackers N] [--duration N]` | Inject Scenario 3: DDoS |
| `./recover.sh <profile>` | Full recovery |
| `./recover.sh <profile> --verify-only` | Health check only |

### Python Scripts (direct invocation)

| Script | Options |
|--------|---------|
| `inject_bad_query.py` | `--profile`, `--cluster`, `--region` |
| `inject_memory_sidecar.py` | `--profile`, `--cluster`, `--region`, `--target` (default: fraud-service) |
| `inject_ddos.py` | `--profile`, `--cluster`, `--region`, `--attackers` (default: 3), `--duration` (default: 300s) |
| `recover_all.py` | `--profile`, `--cluster`, `--region`, `--verify-only` |
