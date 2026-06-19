# DevOps Agent Demo — End-to-End Walkthrough

## 🎯 Demo Objective

Demonstrate how the AWS DevOps Agent autonomously detects, diagnoses, and recommends remediation for three progressively complex production incidents in a real microservices application.

**Story Arc**: Data-layer stress → Resource exhaustion → External attack

---

## 📋 Agenda (30 minutes)

| # | Section | Duration | What You Show |
|---|---------|----------|---------------|
| 1 | Application Walkthrough | 5 min | Platform overview, all personas, claim lifecycle |
| 2 | Observability Setup | 2 min | CloudWatch dashboard, alarms, service health |
| 3 | Introduce DevOps Agent | 3 min | Agent space, webhook, capabilities |
| 4 | Scenario 1: Bad Query | 6 min | Inject → Agent investigates → Recover |
| 5 | Scenario 2: Memory OOM | 6 min | Inject → Agent investigates → Recover |
| 6 | Scenario 3: DDoS Attack | 6 min | Inject → Agent investigates → Recover |
| 7 | Wrap-up | 2 min | Key takeaways |

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS                                            │
│         Policyholder          Adjudicator           Admin                     │
└──────────────┬───────────────────┬──────────────────┬────────────────────────┘
               │                   │                  │
               ▼                   ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AMAZON CLOUDFRONT (CDN)                               │
│                    https://<your-cloudfront-domain>.cloudfront.net                      │
│              ┌──────────────┐         ┌──────────────────┐                   │
│              │  S3 (React   │         │  ALB (API calls) │                   │
│              │  Frontend)   │         │  /api/*           │                   │
│              └──────────────┘         └────────┬─────────┘                   │
└────────────────────────────────────────────────┼─────────────────────────────┘
                                                 │
┌────────────────────────────────────────────────┼─────────────────────────────┐
│                    APPLICATION LOAD BALANCER                                   │
│              Path-based routing to 7 microservices                            │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬─────┘
       │          │          │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼          ▼          ▼
┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
│   Auth   ││  Claims  ││  Fraud   ││ Document ││  Notif.  ││  Rules   ││Analytics │
│ Service  ││ Service  ││ Service  ││ Service  ││ Service  ││ Service  ││ Service  │
│          ││          ││          ││          ││          ││          ││          │
│ JWT/RBAC ││Lifecycle ││ Bedrock  ││ Textract ││ SES/SNS  ││ Engine   ││QuickSight│
└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘
     │           │           │           │           │           │           │
     ▼           ▼           ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ECS FARGATE CLUSTER                                   │
│              7 services × 0.5 vCPU × 1GB RAM (auto-scale 1→3)               │
└─────────────────────────────────────────────────────────────────────────────┘
     │           │           │           │           │           │           │
     ▼           ▼           ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐  ┌──────────────────────┐  │
│  │  DynamoDB   │  │    Aurora     │  │   S3    │  │   AWS Managed        │  │
│  │ (12 tables) │  │ PostgreSQL   │  │(Docs +  │  │   Services           │  │
│  │  On-Demand  │  │  (Analytics) │  │Frontend)│  │ Bedrock, Textract,   │  │
│  │             │  │              │  │         │  │ Comprehend, SES, SNS │  │
│  └─────────────┘  └──────────────┘  └─────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
     │                                                                     │
     ▼                                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  CloudWatch  │  │   X-Ray      │  │  CloudWatch  │  │  Operations  │   │
│  │    Logs      │  │  Tracing     │  │   Alarms     │  │  Dashboard   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Three Fault Scenarios — Story Arc

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   SCENARIO 1     │     │   SCENARIO 2     │     │   SCENARIO 3     │
│                  │     │                  │     │                  │
│   Bad Query      │ ──► │  Memory Sidecar  │ ──► │   DDoS Attack    │
│   (High CPU)     │     │  (OOM Kill)      │     │   (HTTP Flood)   │
│                  │     │                  │     │                  │
│  claim-service   │     │  fraud-service   │     │  claim-service   │
│  Data-layer      │     │  Resource        │     │  External        │
│  stress          │     │  exhaustion      │     │  attack          │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

| Scenario | Target | Fault Type | Root Cause | Alarm Signal |
|----------|--------|-----------|------------|--------------|
| 1 | claim-service | CPU burn | Expensive INNER JOIN query | ECS CPU > 80% |
| 2 | fraud-service | OOM crash loop | ML model sidecar memory leak | Task stopped: OutOfMemoryError |
| 3 | claim-service | Traffic flood | DDoS from rogue ECS tasks | ALB request spike, elevated latency |

---

## Section 1: Application Walkthrough (5 min)

### Open: https://<your-cloudfront-domain>.cloudfront.net

### Narrative

> "This is ClaimFlow — an AI-powered insurance claim processing platform running on AWS. 7 microservices, 4 insurance types, full lifecycle from filing to settlement."

### Step 1.1: Policyholder Flow

1. Click **"Policyholder"** → Login: `testuser2` / `REDACTED-TEST-VALUE`
2. Click **"File New Claim"** → Select **Health Insurance** → Continue
3. Enter: Amount `75000`, Description: `Hospitalization for appendicitis surgery at Apollo Hospital Mumbai`
4. Continue through → **Submit**

> "Claim submitted. Immediately moves to 'Under Review'. The policyholder tracks it in real-time."

5. Click the claim → Show **Claim Journey** timeline
6. **Logout**

### Step 1.2: Adjudicator Flow

1. Click **"Claims Adjudicator"** → Login: `adjudicator1` / `REDACTED-TEST-VALUE`
2. Click the health claim → **Approve** (settlement: `70000`) → **Initiate Settlement** → **Close Claim**
3. Show completed timeline: Draft → Under Review → Approved → Settlement → Closed
4. **Logout**

### Step 1.3: Admin Flow

1. Click **"System Admin"** → Login: `admin1` / `Admin12345`
2. Show **Dashboard**: service health grid (all green), API response times
3. Click **"🎬 Simulate Claim Lifecycle"** to show one-click simulation
4. Navigate to **Analytics** → Show charts

> "All 7 services healthy. Response times under 200ms. This is our baseline — everything working perfectly."

---

## Section 2: Observability Setup (2 min)

### Narrative

> "Behind the scenes: comprehensive monitoring. CloudWatch dashboard, alarms on every layer."

### Show

1. **CloudWatch Dashboard**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ClaimFlow-Operations
   - ECS CPU/Memory graphs (flat)
   - DynamoDB capacity (low)
   - ALB response times (< 200ms)
   - Error counts (zero)

2. **CloudWatch Alarms**: All green, all OK state

> "42 alarms covering ECS CPU, memory, DynamoDB throttles, ALB errors, CloudFront. All green. This is the 'before' state."

---

## Section 3: Introduce DevOps Agent (3 min)

### Narrative

> "Now the AWS DevOps Agent. This is an autonomous, always-on agent wired into our alarms. When something breaks, it starts investigating automatically — no one has to ask."

### Show

1. **Agent Space**: `ClaimFlow-Operations`
2. **Webhook flow**:

```
CloudWatch Alarm → SNS Topic → Lambda → HMAC Webhook → DevOps Agent
```

> "The agent knows our architecture — all 7 services, the DynamoDB tables, the ALB routing. When an alarm fires, it picks it up in seconds and starts correlating signals across the entire stack."

3. Show **Skills/Runbook** section
4. (Optional) Show **Slack integration**

---

## Section 4: Scenario 1 — Bad Query (High CPU) (6 min)

### Narrative

> "First fault: a data-layer issue. A developer deployed a poorly optimized query — an INNER JOIN across policy tables, claim history, and adjudication records. This is a realistic production issue in claims systems."

### Inject

```bash
cd scripts/fault-injection
./inject.sh 1 my-profile
```

> "I've injected a CPU-intensive process into the claim-service that simulates this expensive query."

### Wait & Show Degradation (2-3 min)

1. **Admin Dashboard** → claim-service CPU climbing
2. **CloudWatch** → CPU alarm firing on claim-service
3. **App** → `/api/claims` responses getting slower

> "CPU alarm is firing. The DevOps Agent webhook just received it."

### DevOps Agent Investigation

1. Open **Agent Console** → Active investigation
2. Walk through findings:
   - **Signal**: ECS CPU alarm on claim-service (>80%)
   - **Investigation**: Checked task definition, found `bad-query-simulator` sidecar
   - **Root Cause**: Additional container running expensive computation alongside main application
   - **Impact**: API latency degraded on all `/api/claims/*` endpoints
   - **Recommendation**: Remove the `bad-query-simulator` container, revert task definition

> "In seconds, the agent identified the exact issue — a rogue sidecar process burning CPU. A human would need to check metrics, then logs, then task definitions. The agent did it automatically."

### Recover Before Next Scenario

```bash
./recover.sh my-profile
```

> "Recovering claim-service to its clean state before we move to the next scenario."

Wait 60-90 seconds. Verify admin dashboard shows claim-service green again.

---

## Section 5: Scenario 2 — Memory Sidecar OOM (6 min)

### Narrative

> "Second fault: resource exhaustion. Claims systems often have sidecar containers for fraud-detection ML models or document parsing. A misconfigured sidecar that leaks memory is a common operational risk."

### Inject

```bash
./inject.sh 2 my-profile
```

> "I've added a misconfigured ML model loader sidecar to the fraud-service. It will progressively allocate memory until it crashes the task."

### Wait & Show Degradation (2-3 min)

1. **ECS Console** → fraud-service task cycling (start → crash → restart)
2. **CloudWatch Logs** → `[ml-model-loader] Cached 50MB... 100MB... 200MB...` then task stops
3. **Admin Dashboard** → fraud-service going red
4. **App** → `/api/fraud/*` returning errors

> "The task keeps crashing and restarting — a classic OOM crash loop. Fraud detection is completely down."

### DevOps Agent Investigation

1. Open **Agent Console** → New investigation (or updated existing)
2. Walk through findings:
   - **Signal**: fraud-service task stopped with `OutOfMemoryError`, repeated restarts
   - **Investigation**: Examined stopped task reason, found `ml-model-loader` container
   - **Root Cause**: Sidecar container (`ml-model-loader`) progressively allocating memory until hitting task limit
   - **Impact**: fraud-service in crash loop, all fraud detection requests failing
   - **Recommendation**: Remove `ml-model-loader` sidecar, increase memory limit if model is legitimate, or add memory limits to sidecar

> "The agent correlated the OOM kill reason with the specific container causing it. It didn't just say 'memory is high' — it pinpointed which container, what it was doing, and why the task died."

### Recover Before Next Scenario

```bash
./recover.sh my-profile
```

> "Recovering fraud-service before the final scenario."

Wait 60-90 seconds. Verify admin dashboard shows fraud-service green again.

---

## Section 6: Scenario 3 — DDoS Attack (6 min)

### Narrative

> "Third fault: an external attack. Claims portals are public-facing and susceptible to volumetric attacks. This simulates a DDoS hitting our claim-service through HTTP flood."

### Inject

```bash
./inject.sh 3 my-profile
```

> "I've launched 3 attacker tasks inside the VPC that are flooding the claim-service with requests — 60-300 requests per second total."

### Wait & Show Degradation (1-2 min)

1. **CloudWatch Dashboard** → ALB request count spiking dramatically
2. **ECS Metrics** → claim-service CPU rising (legitimate processing overwhelmed)
3. **Admin Dashboard** → Response times climbing, possible errors
4. **CloudWatch Alarms** → ALB latency alarm, possibly 5xx alarm

> "Request volume just exploded. The service is getting overwhelmed. Latency is climbing, errors starting to appear."

### DevOps Agent Investigation

1. Open **Agent Console** → New investigation
2. Walk through findings:
   - **Signal**: ALB request spike, elevated latency, potential 5xx errors
   - **Investigation**: Examined ECS cluster, found unexpected `ddos-attacker` tasks running
   - **Root Cause**: 3 rogue tasks (`ddos-attacker` family) flooding claim-service with HTTP requests from within the VPC
   - **Impact**: claim-service overwhelmed, elevated latency and errors for legitimate users
   - **Recommendation**: Stop `ddos-attacker` tasks, investigate how they were launched, consider WAF rate limiting

> "The agent didn't just see 'high traffic.' It traced the source — found the attacker tasks by name, identified they're not part of our normal services, and recommended stopping them. It correlated the traffic spike with the new tasks appearing in the cluster."

### Final Recovery

```bash
./recover.sh my-profile
```

> "Recovering the system. All clean, ready for the next demo."

---

## Section 7: Wrap-up (2 min)

### Key Takeaways

> "Let me summarize what we saw across three scenarios:"

1. **Scenario 1 (Bad Query)**: Data-layer issue. Agent identified a rogue CPU-burning sidecar in the task definition. Found in seconds vs. 15+ minutes manual investigation.

2. **Scenario 2 (OOM Sidecar)**: Resource exhaustion. Agent correlated the OOM kill reason with the specific container and its memory allocation pattern. Pinpointed root cause, not just the symptom.

3. **Scenario 3 (DDoS)**: External attack. Agent detected abnormal traffic, traced it to unauthorized tasks in the cluster, and distinguished attack traffic from legitimate requests.

> "Three different failure modes. Three different root causes. The DevOps Agent handled all of them autonomously — no human needed to notice, login, or start investigating."
>
> "That's the shift: from reactive firefighting to autonomous operations."

---

## 🔧 Pre-Demo Checklist

- [ ] Platform accessible: https://<your-cloudfront-domain>.cloudfront.net
- [ ] All 3 test accounts work (policyholder, adjudicator, admin)
- [ ] Admin dashboard shows all 7 services green
- [ ] CloudWatch dashboard loads with healthy metrics
- [ ] CloudWatch alarms all in OK state
- [ ] DevOps Agent Space configured (`ClaimFlow-Operations`)
- [ ] Webhook active and Lambda deployed
- [ ] Terminal ready at `scripts/fault-injection/`
- [ ] Run verify to confirm clean state:
  ```bash
  cd scripts/fault-injection
  ./recover.sh my-profile --verify-only
  ```
- [ ] (Optional) Slack channel connected
- [ ] Analytics sync done: `POST /api/analytics/sync`

---

## 🚨 Emergency Recovery

If anything goes wrong during the demo:

```bash
cd scripts/fault-injection
./recover.sh my-profile
```

Verify after 90 seconds:
```bash
./recover.sh my-profile --verify-only
```

---

## 📝 Demo Variants

### Quick Demo (15 min)
- Show app briefly (2 min)
- Pick 1 scenario (Scenario 1 is fastest to show) (5 min)
- Show agent investigation (5 min)
- Recover (3 min)

### Executive Demo (10 min)
- Architecture diagram (1 min)
- Show healthy state → inject Scenario 3 (DDoS — most visually dramatic) (3 min)
- Agent investigation results (4 min)
- Recover + business value (2 min)
- Key message: "Autonomous operations. 30 seconds vs. 30 minutes."

### Extended Demo (45 min)
- Full app walkthrough with all personas (10 min)
- Show CDK infrastructure code briefly (3 min)
- Run all 3 scenarios sequentially with full agent walkthrough (25 min)
- Discuss mitigation plans and auto-remediation potential (5 min)
- Q&A (2 min)

### Single Scenario Focus
If you only have time for one scenario:
- **Technical audience**: Scenario 2 (OOM) — most relatable operational issue
- **Security audience**: Scenario 3 (DDoS) — shows threat detection
- **Developer audience**: Scenario 1 (Bad Query) — shows code-level impact detection
