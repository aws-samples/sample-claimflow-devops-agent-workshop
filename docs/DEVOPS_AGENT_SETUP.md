# AWS DevOps Agent — Auto-Investigation Setup Guide

## Overview

This guide sets up AWS DevOps Agent to **automatically investigate** when CloudWatch alarms fire for the ClaimFlow platform. The flow is:

```
CloudWatch Alarm fires → EventBridge → Lambda → Webhook → DevOps Agent investigates
```

No human intervention needed. The agent starts investigating the moment an alarm transitions to ALARM state.

---

## Prerequisites

- AWS DevOps Agent access (sign up at https://aws.amazon.com/devops-agent/)
- AWS Account: 123456789012 (us-east-1)
- 42 CloudWatch alarms already created (prefix: `ClaimFlow-`)
- SNS Topic: `arn:aws:sns:us-east-1:123456789012:claim-processing-alarms`

---

## Step 1: Create an Agent Space

1. Go to **AWS DevOps Agent Console** → https://console.aws.amazon.com/devopsagent/
2. Click **Create Agent Space**
3. Name: `ClaimFlow-Operations`
4. Description: `Autonomous investigation for ClaimFlow insurance platform (7 microservices, ECS Fargate, DynamoDB, ALB)`
5. Add your AWS account: `123456789012`
6. Region: `us-east-1`
7. Click **Create**

---

## Step 2: Create a Webhook

1. In your Agent Space page → Click **Capabilities**
2. Scroll to **Webhooks** section
3. Click **Add** → Generate webhook
4. The system generates an HMAC key pair
5. **Save the webhook URL and secret key** securely (you won't see the secret again)

Example webhook URL format:
```
https://hooks.devopsagent.us-east-1.amazonaws.com/spaces/<space-id>/webhooks/<webhook-id>
```

---

## Step 3: Create Lambda Function (Webhook Forwarder)

This Lambda receives SNS notifications from CloudWatch alarms and forwards them to the DevOps Agent webhook.

### 3.1 Create the Lambda

```bash
AWS_PROFILE=my-profile aws lambda create-function \
  --function-name ClaimFlow-DevOpsAgent-Webhook \
  --runtime nodejs20.x \
  --role arn:aws:iam::123456789012:role/lambda-basic-execution \
  --handler index.handler \
  --timeout 30 \
  --environment "Variables={WEBHOOK_URL=<your-webhook-url>,WEBHOOK_SECRET=<your-webhook-secret>}" \
  --zip-file fileb://lambda-webhook.zip \
  --tags Project=claim-processing,auto-delete=no
```

### 3.2 Lambda Code (`index.mjs`)

```javascript
import { createHmac } from "node:crypto";

export const handler = async (event) => {
  const webhookUrl = process.env.WEBHOOK_URL;
  const webhookSecret = process.env.WEBHOOK_SECRET;

  // Parse SNS message (from CloudWatch Alarm)
  for (const record of event.Records) {
    const snsMessage = JSON.parse(record.Sns.Message);
    
    const payload = {
      eventType: "incident",
      incidentId: snsMessage.AlarmName + "-" + Date.now(),
      action: "created",
      priority: snsMessage.NewStateValue === "ALARM" ? "HIGH" : "LOW",
      title: `CloudWatch Alarm: ${snsMessage.AlarmName}`,
      description: snsMessage.AlarmDescription || snsMessage.NewStateReason,
      timestamp: new Date().toISOString(),
      service: "ClaimFlow",
      data: {
        alarmName: snsMessage.AlarmName,
        newState: snsMessage.NewStateValue,
        oldState: snsMessage.OldStateValue,
        reason: snsMessage.NewStateReason,
        metric: snsMessage.Trigger?.MetricName,
        namespace: snsMessage.Trigger?.Namespace,
        region: snsMessage.Region,
        accountId: snsMessage.AWSAccountId,
      },
    };

    // Sign the payload with HMAC
    const timestamp = new Date().toISOString();
    const hmac = createHmac("sha256", webhookSecret);
    hmac.update(`${timestamp}:${JSON.stringify(payload)}`, "utf8");
    const signature = hmac.digest("base64");

    // Send to DevOps Agent webhook
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-amzn-event-timestamp": timestamp,
        "x-amzn-event-signature": signature,
      },
      body: JSON.stringify(payload),
    });

    console.log(`Sent to DevOps Agent: ${response.status} ${snsMessage.AlarmName}`);
  }

  return { statusCode: 200 };
};
```

### 3.3 Package and Deploy

```bash
# Create the Lambda package
mkdir -p /tmp/lambda-webhook
cat > /tmp/lambda-webhook/index.mjs << 'EOF'
// (paste the code above)
EOF

cd /tmp/lambda-webhook
zip -r lambda-webhook.zip index.mjs
aws lambda update-function-code \
  --function-name ClaimFlow-DevOpsAgent-Webhook \
  --zip-file fileb://lambda-webhook.zip \
  --profile my-profile
```

---

## Step 4: Subscribe Lambda to SNS Topic

```bash
AWS_PROFILE=my-profile aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:claim-processing-alarms \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456789012:function:ClaimFlow-DevOpsAgent-Webhook
```

Grant SNS permission to invoke Lambda:

```bash
AWS_PROFILE=my-profile aws lambda add-permission \
  --function-name ClaimFlow-DevOpsAgent-Webhook \
  --statement-id sns-invoke \
  --action lambda:InvokeFunction \
  --principal sns.amazonaws.com \
  --source-arn arn:aws:sns:us-east-1:123456789012:claim-processing-alarms
```

---

## Step 5: Add DevOps Agent Skills (Optional but Recommended)

Create a skill to guide the agent's investigation for ClaimFlow:

### Skill: `claimflow-runbook.md`

```markdown
# ClaimFlow Investigation Runbook

## Application Context
- Platform: ClaimFlow Insurance Claim Processing
- Architecture: 7 microservices on ECS Fargate
- Database: DynamoDB (12 tables) + Aurora PostgreSQL
- Routing: CloudFront → ALB → ECS services
- Region: us-east-1
- ECS Cluster: claim-processing-cluster

## Services
| Service | Path | Purpose |
|---------|------|---------|
| Auth Service | /api/auth/* | Authentication, JWT tokens |
| Claim Service | /api/claims/* | Claim lifecycle management |
| Fraud Service | /api/fraud/* | AI fraud detection (Bedrock) |
| Document Service | /api/documents/* | Document upload, OCR |
| Notification Service | /api/notifications/* | Email + SMS |
| Rules Service | /api/rules/* | Assessment rules engine |
| Analytics Service | /api/analytics/* | Data aggregation |

## Investigation Steps
1. Check which CloudWatch alarms are in ALARM state (prefix: ClaimFlow-)
2. Check ECS cluster task counts — are any services at 0 tasks?
3. Check ECS CPU/Memory utilization — any above 80%?
4. Check DynamoDB throttled requests — any tables being throttled?
5. Check ALB target health — any unhealthy targets?
6. Check ALB 5xx error count — elevated errors?
7. Check CloudWatch Logs for error patterns in /claim-processing/* log groups
8. Correlate: Which service is the root cause?

## Common Issues
- High CPU on ECS: Traffic spike or resource-intensive operation
- DynamoDB throttling: Burst capacity exceeded, consider provisioned mode
- ALB 5xx: Backend service crashed or unreachable
- Unhealthy targets: ECS task failed health check, check logs
- Service at 0 tasks: Deployment failure or manual scale-down

## Remediation
- Scale up ECS service: aws ecs update-service --desired-count 2
- Check logs: aws logs get-log-events --log-group-name /claim-processing/{service}
- Restart task: aws ecs stop-task (ECS will auto-restart)
```

Upload this skill in the DevOps Agent Operator Console → Skills → Add skill.

---

## Step 6: Connect Slack (Optional)

1. DevOps Agent Console → Settings → Communications
2. Click **Register** → Authorize Slack workspace
3. Go to Agent Space → Communications → Add integration
4. Enter your Slack channel ID
5. In Slack, type: `/invite @AWS DevOps Agent`

Now the agent posts investigation findings to your Slack channel.

---

## Step 7: Test Auto-Investigation

### Trigger an Alarm

```bash
cd scripts/stress-testing

# Option 1: Kill services (fastest alarm trigger)
python stress_ecs.py --profile my-profile --action scale-down

# Option 2: API flood (triggers CPU alarms)
python stress_api.py --profile my-profile --duration 180 --rps 50
```

### Verify the Flow

1. **CloudWatch Alarms** → Watch alarms transition to 🔴 ALARM (1-2 min)
2. **SNS** → Notification sent to topic
3. **Lambda** → Invoked, forwards to webhook (check Lambda logs)
4. **DevOps Agent** → Investigation auto-created
5. **Operator Console** → See active investigation with findings
6. **Slack** (if configured) → Agent posts root cause analysis

### Recover

```bash
python recover_all.py --profile my-profile
```

---

## Complete Flow Diagram

```
┌──────────────────┐     ┌─────────────┐     ┌──────────────┐
│  CloudWatch      │     │    SNS      │     │   Lambda     │
│  Alarm fires     │────▶│   Topic     │────▶│  (Forwarder) │
│  (ClaimFlow-*)   │     │             │     │              │
└──────────────────┘     └─────────────┘     └──────┬───────┘
                                                     │
                                                     │ HMAC-signed webhook
                                                     ▼
                                            ┌──────────────────┐
                                            │  AWS DevOps      │
                                            │  Agent           │
                                            │                  │
                                            │  • Reads CW      │
                                            │    metrics       │
                                            │  • Checks ECS    │
                                            │    tasks         │
                                            │  • Queries DDB   │
                                            │  • Checks ALB    │
                                            │  • Reads logs    │
                                            │                  │
                                            │  → Root Cause    │
                                            │  → Mitigation    │
                                            │    Plan          │
                                            └────────┬─────────┘
                                                     │
                                            ┌────────▼─────────┐
                                            │  Slack Channel   │
                                            │  (findings +     │
                                            │   recommendations)│
                                            └──────────────────┘
```

---

## Summary

| Component | Purpose | Status |
|-----------|---------|--------|
| Agent Space | Investigation scope | Create in console |
| Webhook | Receives alarm events | Generate in Agent Space |
| Lambda | Forwards SNS → Webhook | Deploy with code above |
| SNS Subscription | Connects alarms to Lambda | CLI command |
| Skills | Guides investigation | Upload runbook |
| Slack | Team notifications | Optional integration |
| CloudWatch Alarms (42) | Trigger source | ✅ Already created |
| Stress Scripts | Test triggers | ✅ Already created |

Once set up, the entire flow is **fully autonomous** — alarm fires, agent investigates, findings posted — no human needed to start the process.
