# Third-Party Observability Integration Guide

## Overview

This guide covers setting up **Splunk** and **Datadog** from scratch, forwarding ClaimFlow logs to them, and integrating with AWS DevOps Agent for cross-platform investigation.

```
ClaimFlow Services → CloudWatch Logs → Subscription Filter → Datadog Forwarder Lambda → Datadog
                                                                                      │
                                                                                      ▼
                                                                            AWS DevOps Agent
                                                                            (MCP integration)
```

## Current Deployment Status

| Component | Status | Details |
|-----------|:------:|---------|
| Datadog Forwarder Lambda | ✅ Deployed | `datadog-forwarder` in us-east-1 |
| Log Group Subscriptions | ✅ All 7 subscribed | Subscription filter on each log group |
| Log Group Tags | ✅ Set | `service=claim-processing:<name>` on each group |
| DD_FETCH_LOG_GROUP_TAGS | ✅ Enabled | Forwarder reads tags for service name |
| Datadog API Key | ✅ Configured | Set in Lambda env vars |
| Analytics Aurora Table | ✅ Initialized | `claims_analytics` table created via sync |
| Notification IAM Fix | ✅ Applied | `dynamodb:Scan` added to task role |

## Datadog Log Filters

| What | Filter |
|------|--------|
| All ClaimFlow logs | `@aws.cloudwatch.log_group:/claim-processing/*` |
| Auth service | `@aws.cloudwatch.log_group:/claim-processing/auth-service` |
| Claim service | `@aws.cloudwatch.log_group:/claim-processing/claim-service` |
| Fraud service | `@aws.cloudwatch.log_group:/claim-processing/fraud-service` |
| Document service | `@aws.cloudwatch.log_group:/claim-processing/document-service` |
| Notification service | `@aws.cloudwatch.log_group:/claim-processing/notification-service` |
| Rules service | `@aws.cloudwatch.log_group:/claim-processing/rules-service` |
| Analytics service | `@aws.cloudwatch.log_group:/claim-processing/analytics-service` |
| Errors only | `@aws.cloudwatch.log_group:/claim-processing/* status:error` |
| HTTP requests | `@aws.cloudwatch.log_group:/claim-processing/* "HTTP"` |

## Generating Traffic for Logs

```bash
# Generate demo traffic by filing claims through the application UI,
# or drive the API directly with your own script against the deployed endpoint.

# Stress test (high volume)
cd scripts/stress-testing
python3 stress_api.py --profile my-profile --duration 60 --rps 10

# Option 3: Admin UI simulate button
# Login as admin1 → Dashboard → Click "🎬 Simulate Claim Lifecycle"
```

## Known Issues & Fixes Applied

| Issue | Fix |
|-------|-----|
| Service shows as `cloudwatch` in Datadog | Log groups tagged with `service=claim-processing:<name>`, `DD_FETCH_LOG_GROUP_TAGS=true` |
| Analytics `UndefinedTable` error | Run `POST /api/analytics/sync` to create Aurora table |
| Notification `AccessDeniedException` on Scan | Added `dynamodb:Scan` IAM inline policy to task role |
| CloudFront returns HTML for `/api/*` calls | Re-added `/api/*` cache behavior with ALB origin |

---

# Part 1: Datadog Setup

## Why Datadog?
- Cloud-native monitoring platform
- Easy AWS integration (no infrastructure to manage)
- Free 14-day trial available
- DevOps Agent integrates via native Datadog connection

## Current Setup (Already Deployed)

| Component | Value |
|-----------|-------|
| Forwarder Lambda | `datadog-forwarder` (CloudFormation stack: `datadog-forwarder`) |
| API Key | Configured in Lambda env vars |
| Site | `datadoghq.com` (US1) |
| Log Groups Subscribed | 7 (all ClaimFlow services) |
| Service Tag Source | CloudWatch Log Group tags (`DD_FETCH_LOG_GROUP_TAGS=true`) |
| Service Name Format | `claim-processing:<service-name>` |

---

### Step 1.1: Create Datadog Account

1. Go to https://www.datadoghq.com/free-datadog-trial/
2. Sign up with your email
3. Choose region: **US1** (us-east-1 compatible)
4. Complete the onboarding wizard
5. You'll get:
   - **API Key** (for sending data)
   - **Application Key** (for reading data)
   - Save both — you'll need them

### Step 1.2: Install AWS Integration in Datadog

1. In Datadog → **Integrations** → Search "AWS"
2. Click **Amazon Web Services** → **Install**
3. Click **Add AWS Account**
4. Choose **CloudFormation** method (easiest):
   - Datadog provides a CloudFormation template URL
   - Run it in your AWS account (123456789012)
   - It creates an IAM role that Datadog assumes to read metrics
5. After stack completes, Datadog starts pulling CloudWatch metrics automatically

**What you get immediately:**
- ECS CPU/Memory metrics in Datadog
- DynamoDB metrics
- ALB metrics
- All without any code changes

### Step 1.3: Send CloudWatch Logs to Datadog

**Option A: Datadog Forwarder Lambda (Recommended)**

```bash
# Deploy the Datadog Forwarder Lambda via CloudFormation
AWS_PROFILE=my-profile aws cloudformation create-stack \
  --stack-name datadog-forwarder \
  --template-url https://datadog-cloudformation-template.s3.amazonaws.com/aws/forwarder/latest.yaml \
  --parameters \
    ParameterKey=DdApiKey,ParameterValue=<YOUR_DATADOG_API_KEY> \
    ParameterKey=DdSite,ParameterValue=datadoghq.com \
    ParameterKey=FunctionName,ParameterValue=datadog-forwarder \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --tags Key=Project,Value=claim-processing Key=auto-delete,Value=no
```

Wait for stack to complete (~3 min):
```bash
AWS_PROFILE=my-profile aws cloudformation wait stack-create-complete --stack-name datadog-forwarder
```

**Subscribe ClaimFlow log groups to the forwarder:**

```bash
FORWARDER_ARN=$(AWS_PROFILE=my-profile aws lambda get-function --function-name datadog-forwarder --query 'Configuration.FunctionArn' --output text)

# Subscribe all 7 service log groups
for service in auth-service claim-service fraud-service document-service notification-service rules-service analytics-service; do
  AWS_PROFILE=my-profile aws logs put-subscription-filter \
    --log-group-name "/claim-processing/$service" \
    --filter-name "datadog-forwarder" \
    --filter-pattern "" \
    --destination-arn "$FORWARDER_ARN"
  echo "Subscribed: /claim-processing/$service"
done
```

### Step 1.4: Verify Logs in Datadog

1. Go to Datadog → **Logs** → **Live Tail**
2. Filter: `@aws.cloudwatch.log_group:/claim-processing/*`
3. You should see logs from all 7 services
4. Service names appear as `claim-processing:auth-service`, `claim-processing:claim-service`, etc.

**Note**: Service name comes from CloudWatch Log Group tags (set on AWS side). The `DD_FETCH_LOG_GROUP_TAGS=true` env var on the forwarder Lambda enables this.

### Step 1.5: Create Datadog Monitors (Alarms)

In Datadog → **Monitors** → **New Monitor**:

**Monitor 1: High ECS CPU**
- Type: Metric
- Metric: `aws.ecs.cpuutilization`
- Filter: `clustername:claim-processing-cluster`
- Alert threshold: > 80%
- Notify: Your email or Slack

**Monitor 2: High Error Rate**
- Type: Log
- Query: `service:claim-processing* status:error`
- Alert threshold: > 10 errors in 5 min

**Monitor 3: Service Down**
- Type: Metric
- Metric: `aws.ecs.running_task_count`
- Filter: `clustername:claim-processing-cluster`
- Alert threshold: < 1

### Step 1.6: Integrate Datadog with AWS DevOps Agent

1. In **AWS DevOps Agent Console** → Your Agent Space → **Capabilities**
2. Click **Add** under **Monitoring**
3. Select **Datadog**
4. Enter:
   - Datadog Site: `datadoghq.com`
   - API Key: `<your-api-key>`
   - Application Key: `<your-app-key>`
5. Click **Connect**

Now the DevOps Agent can query Datadog metrics and logs during investigations.

### Step 1.7: Configure Datadog → DevOps Agent Webhook

To auto-trigger investigations from Datadog alerts:

1. In Datadog → **Integrations** → **Webhooks**
2. Click **New Webhook**
3. Name: `devops-agent-webhook`
4. URL: `<your-devops-agent-webhook-url>`
5. Custom Headers:
   ```
   Content-Type: application/json
   ```
6. Payload:
   ```json
   {
     "eventType": "incident",
     "incidentId": "$ALERT_ID",
     "action": "created",
     "priority": "$ALERT_PRIORITY",
     "title": "$ALERT_TITLE",
     "description": "$ALERT_DESCRIPTION",
     "timestamp": "$DATE",
     "service": "ClaimFlow",
     "data": {
       "source": "datadog",
       "alertId": "$ALERT_ID",
       "alertMetric": "$ALERT_METRIC",
       "alertScope": "$ALERT_SCOPE"
     }
   }
   ```
7. In each Datadog Monitor → Notification → Add `@webhook-devops-agent-webhook`

---

# Part 2: Splunk Setup

## Why Splunk?
- Industry-standard log analytics
- Powerful search (SPL)
- DevOps Agent integrates via Splunk MCP Server
- Free trial: Splunk Cloud (15-day) or Splunk Enterprise (60-day)

---

### Step 2.1: Create Splunk Account

**Option A: Splunk Cloud (Easiest for demo)**
1. Go to https://www.splunk.com/en_us/download/splunk-cloud.html
2. Sign up for free trial
3. You'll get a Splunk Cloud instance URL: `https://<your-instance>.splunkcloud.com`
4. Login with your credentials

**Option B: Splunk Enterprise on EC2 (More control)**
1. Launch an EC2 instance (t3.medium, Amazon Linux 2023)
2. Security group: Allow inbound 8000 (web), 8088 (HEC), 8089 (management)
3. SSH in and install:
```bash
wget -O splunk.tgz "https://download.splunk.com/products/splunk/releases/9.2.0/linux/splunk-9.2.0-7c8e1cb5-Linux-x86_64.tgz"
tar -xzf splunk.tgz -C /opt
/opt/splunk/bin/splunk start --accept-license --answer-yes --seed-passwd YourPassword123
```
4. Access at: `http://<ec2-public-ip>:8000`

### Step 2.2: Configure HTTP Event Collector (HEC)

HEC is how you send logs to Splunk.

1. In Splunk → **Settings** → **Data Inputs** → **HTTP Event Collector**
2. Click **Global Settings**:
   - Enable: ✅
   - Default Source Type: `_json`
   - Click **Save**
3. Click **New Token**:
   - Name: `claimflow-logs`
   - Source Type: `_json`
   - Index: `main` (or create a new index called `claimflow`)
   - Click **Submit**
4. **Copy the token** — you'll need it for the forwarder

HEC endpoint: `https://<your-splunk>:8088/services/collector/event`

### Step 2.3: Send CloudWatch Logs to Splunk

**Using Kinesis Firehose (AWS-managed, no code):**

```bash
# Step 1: Create Firehose delivery stream to Splunk
AWS_PROFILE=my-profile aws firehose create-delivery-stream \
  --delivery-stream-name ClaimFlow-to-Splunk \
  --splunk-destination-configuration '{
    "HECEndpoint": "https://<your-splunk>:8088",
    "HECEndpointType": "Event",
    "HECToken": "<your-hec-token>",
    "S3Configuration": {
      "RoleARN": "arn:aws:iam::123456789012:role/firehose-splunk-role",
      "BucketARN": "arn:aws:s3:::claim-processing-documents-123456789012",
      "Prefix": "splunk-failed/"
    }
  }'
```

**Alternative: Lambda Forwarder (simpler for demo):**

Create a Lambda that forwards CloudWatch Logs to Splunk HEC:

```python
# lambda_splunk_forwarder.py
import json
import base64
import gzip
import urllib.request
import os

SPLUNK_HEC_URL = os.environ['SPLUNK_HEC_URL']
SPLUNK_HEC_TOKEN = os.environ['SPLUNK_HEC_TOKEN']

def handler(event, context):
    # Decode CloudWatch Logs
    payload = base64.b64decode(event['awslogs']['data'])
    log_data = json.loads(gzip.decompress(payload))
    
    # Forward each log event to Splunk
    for log_event in log_data['logEvents']:
        splunk_event = {
            "event": log_event['message'],
            "source": log_data['logGroup'],
            "sourcetype": "_json",
            "time": log_event['timestamp'] / 1000,
        }
        
        req = urllib.request.Request(
            f"{SPLUNK_HEC_URL}/services/collector/event",
            data=json.dumps(splunk_event).encode(),
            headers={
                "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
                "Content-Type": "application/json",
            },
        )
        urllib.request.urlopen(req)
    
    return {"statusCode": 200}
```

Deploy and subscribe log groups (same pattern as Datadog).

### Step 2.4: Verify Logs in Splunk

1. In Splunk → **Search & Reporting**
2. Search: `index=main source="/claim-processing/*"`
3. You should see logs from all 7 services

### Step 2.5: Create Splunk Alerts

In Splunk → **Search & Reporting** → Save As → **Alert**:

**Alert 1: High Error Rate**
- Search: `index=main source="/claim-processing/*" "ERROR" | stats count | where count > 10`
- Schedule: Every 5 minutes
- Trigger: When results > 0

**Alert 2: Service Down**
- Search: `index=main source="/claim-processing/*" "Uvicorn running" earliest=-5m | stats count by source | where count = 0`
- Schedule: Every 5 minutes

### Step 2.6: Enable Splunk MCP Server

The MCP (Model Context Protocol) server allows DevOps Agent to query Splunk directly.

1. In Splunk → **Apps** → **Find More Apps** → Search "MCP Server"
2. Install **Splunk MCP Server** app
3. Configure:
   - Go to **Settings** → **Users** → Create a user with `mcp_user` role
   - Go to **Settings** → **Tokens** → Create authentication token for that user
   - Audience: `mcp`
   - Copy the token
4. Verify MCP endpoint: `https://<your-splunk>:8089/services/mcp`

### Step 2.7: Integrate Splunk with AWS DevOps Agent

1. In **AWS DevOps Agent Console** → Your Agent Space → **Capabilities**
2. Click **Add** under **Monitoring**
3. Select **Custom MCP** (or Splunk if available)
4. Enter MCP configuration:
   ```json
   {
     "url": "https://<your-splunk>:8089/services/mcp",
     "auth": {
       "type": "bearer",
       "token": "<your-mcp-token>"
     }
   }
   ```
5. Click **Connect**

Now the DevOps Agent can search Splunk logs during investigations.

### Step 2.8: Configure Splunk → DevOps Agent Auto-Trigger

1. Install **A Better Webhooks** app in Splunk (Splunkbase)
2. Create a credential:
   - Header Name: `Authorization`
   - Header Value: `Bearer <your-devops-agent-webhook-secret>`
3. In your Splunk alerts → Trigger Actions → Add **Better Webhook**:
   - URL: `<your-devops-agent-webhook-url>`
   - Body:
   ```json
   {
     "eventType": "incident",
     "incidentId": "splunk-$result.sid$",
     "action": "created",
     "priority": "HIGH",
     "title": "Splunk Alert: $name$",
     "description": "$result._raw$",
     "service": "ClaimFlow",
     "data": {"source": "splunk"}
   }
   ```

---

# Part 3: Summary — Complete Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ClaimFlow Platform                                 │
│  7 ECS Services → CloudWatch Logs (/claim-processing/*)             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
              ▼            ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  CloudWatch  │ │   Datadog    │ │    Splunk    │
    │  (Native)    │ │  (Forwarder  │ │  (HEC via    │
    │              │ │   Lambda)    │ │   Lambda)    │
    │  42 Alarms   │ │  Monitors    │ │  Alerts      │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           │   SNS/Lambda   │   Webhook      │  Better Webhooks
           │                │                │
           ▼                ▼                ▼
    ┌─────────────────────────────────────────────────┐
    │              AWS DevOps Agent                     │
    │                                                  │
    │  Capabilities:                                   │
    │  • CloudWatch (native)                           │
    │  • Datadog (API/App key)                         │
    │  • Splunk (MCP Server)                           │
    │                                                  │
    │  Investigation:                                  │
    │  • Correlates across ALL three platforms         │
    │  • Queries CW metrics + Datadog metrics          │
    │  • Searches Splunk logs for error patterns       │
    │  • Provides unified root cause                   │
    └──────────────────────────┬──────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Slack Channel   │
                    │  (Findings)      │
                    └──────────────────┘
```

---

# Part 4: Quick Reference

## Datadog

| Item | Value |
|------|-------|
| Sign up | https://www.datadoghq.com/free-datadog-trial/ |
| Trial | 14 days free |
| AWS Integration | CloudFormation template (auto-pulls metrics) |
| Log Forwarding | Datadog Forwarder Lambda (`datadog-forwarder`) ✅ Deployed |
| Log Group Tags | `service=claim-processing:<name>` ✅ Set |
| Forwarder Env | `DD_FETCH_LOG_GROUP_TAGS=true` ✅ Configured |
| DevOps Agent Integration | API Key + App Key in Agent Space |
| Auto-trigger | Webhook in Datadog Monitors |
| Log Filter | `@aws.cloudwatch.log_group:/claim-processing/*` |

## Splunk

| Item | Value |
|------|-------|
| Sign up | https://www.splunk.com/en_us/download/splunk-cloud.html |
| Trial | 15 days (Cloud) or 60 days (Enterprise) |
| Log Ingestion | HTTP Event Collector (HEC) |
| Log Forwarding | Lambda or Kinesis Firehose |
| DevOps Agent Integration | Splunk MCP Server |
| Auto-trigger | Better Webhooks app → DevOps Agent webhook |

## Time Estimates

| Task | Datadog | Splunk |
|------|---------|--------|
| Account setup | 5 min | 10 min |
| AWS integration | 10 min | 15 min |
| Log forwarding | 15 min | 20 min |
| Alerts/Monitors | 10 min | 10 min |
| DevOps Agent integration | 5 min | 10 min |
| **Total** | **~45 min** | **~65 min** |

---

# Part 5: Demo Narrative Addition

When showing third-party integration in the demo:

> "The DevOps Agent doesn't just work with CloudWatch. It integrates with Datadog and Splunk too. When an incident occurs, it correlates signals across all three platforms — CloudWatch metrics, Datadog APM traces, and Splunk log patterns — to give you a unified root cause analysis."
>
> "This is critical for enterprises that use multiple observability tools. The agent becomes the single pane of glass that connects them all."


---

# Part 6: Maintenance & Troubleshooting

## Common Issues

### Datadog shows `service:cloudwatch` instead of service name
**Cause**: Log group tags not being read by forwarder.
**Fix**:
```bash
# Verify tags are set
AWS_PROFILE=my-profile aws logs list-tags-log-group --log-group-name /claim-processing/auth-service

# Verify forwarder has DD_FETCH_LOG_GROUP_TAGS=true
AWS_PROFILE=my-profile aws lambda get-function-configuration --function-name datadog-forwarder --query 'Environment.Variables.DD_FETCH_LOG_GROUP_TAGS'

# Re-tag if needed
AWS_PROFILE=my-profile aws logs tag-log-group --log-group-name "/claim-processing/auth-service" --tags "service=claim-processing:auth-service"
```

### Analytics service errors (UndefinedTable)
**Cause**: Aurora PostgreSQL `claims_analytics` table not created.
**Fix**:
```bash
TOKEN=$(curl -s -X POST https://<your-cloudfront-domain>.cloudfront.net/api/auth/login -H "Content-Type: application/json" -d '{"user_id":"admin1","password":"Admin12345"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -X POST https://<your-cloudfront-domain>.cloudfront.net/api/analytics/sync -H "Authorization: Bearer $TOKEN"
```

### Notification service AccessDeniedException
**Cause**: Task role missing `dynamodb:Scan` permission.
**Fix**:
```bash
AWS_PROFILE=my-profile aws iam put-role-policy \
  --role-name <notification-task-role-name> \
  --policy-name DynamoDBScanAccess \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["dynamodb:Scan"],"Resource":["arn:aws:dynamodb:us-east-1:123456789012:table/claim-processing-notification-*"]}]}'
```

### CloudFront returns HTML for API calls
**Cause**: `/api/*` cache behavior was removed from CloudFront distribution.
**Fix**: Re-add the behavior pointing to `alb-api` origin (see deployment guide).

### No logs appearing in Datadog
**Cause**: No traffic to services (no log events to forward).
**Fix**: Generate traffic:
```bash
cd scripts/stress-testing
python3 stress_api.py --profile my-profile --duration 30 --rps 5
```

## Useful Commands

```bash
# Check Datadog forwarder Lambda logs
AWS_PROFILE=my-profile aws logs tail /aws/lambda/datadog-forwarder --follow

# Check subscription filters on a log group
AWS_PROFILE=my-profile aws logs describe-subscription-filters --log-group-name /claim-processing/auth-service

# List all log group tags
for svc in auth-service claim-service fraud-service document-service notification-service rules-service analytics-service; do
  echo "=== $svc ===" && AWS_PROFILE=my-profile aws logs list-tags-log-group --log-group-name "/claim-processing/$svc"
done

# Update forwarder environment variable
AWS_PROFILE=my-profile aws lambda update-function-configuration --function-name datadog-forwarder --environment 'Variables={DD_API_KEY=<key>,DD_SITE=datadoghq.com,DD_FETCH_LOG_GROUP_TAGS=true,DD_TAGS=project:claim-processing}'
```
