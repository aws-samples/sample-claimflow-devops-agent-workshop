# Deployment Guide — Claim Processing Services

## Current Deployment

| Attribute | Value |
|-----------|-------|
| **AWS Profile** | `my-profile` |
| **AWS Account** | 123456789012 |
| **Region** | us-east-1 |
| **Frontend URL** | https://<your-cloudfront-domain>.cloudfront.net |
| **CloudFront Distribution** | E2DQJ6HVWVGQCK |
| **ALB DNS** | claim-processing-alb-1129342539.us-east-1.elb.amazonaws.com |
| **ECS Cluster** | claim-processing-cluster |
| **CDK Stacks** | 12 deployed |

## Overview

This guide covers deploying the Claim Processing Services platform to AWS from scratch. The platform consists of 7 backend microservices, a React frontend, and 13 CDK infrastructure stacks.

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.12+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| AWS CDK CLI | 2.x | `cdk --version` |
| AWS CLI | 2.x | `aws --version` |
| Finch or Docker | Latest | `finch --version` or `docker --version` |

### Install CDK CLI (if not installed)
```bash
npm install -g aws-cdk
```

### AWS Profile Setup
```bash
aws configure --profile <your-profile-name>
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

---

## Quick Deploy (One Command)

```bash
./deploy.sh <aws-profile-name>
```

**Example:**
```bash
./deploy.sh my-dev-profile
```

The script will:
1. Validate all prerequisites (Python 3.12+, Node, CDK, AWS credentials)
2. Detect container runtime (finch preferred, docker fallback)
3. Create Python venv and install CDK dependencies
4. Bootstrap CDK in your AWS account
5. Build all 7 backend service container images
6. Build the React frontend
7. Deploy all 13 CDK stacks
8. Print the CloudFront URL for the application

**Expected duration**: 10–15 minutes (first deploy), 5–8 minutes (subsequent deploys)

---

## Manual Deployment (Step by Step)

### Step 1: Bootstrap CDK

```bash
cd infra
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cdk bootstrap aws://<ACCOUNT_ID>/us-east-1 --profile <your-profile>
```

### Step 2: Build Container Images

```bash
# Using finch
for svc in auth-service claim-service document-service fraud-service rules-service notification-service analytics-service; do
  finch build -t claim-processing/$svc:latest services/$svc/
done

# OR using docker
for svc in auth-service claim-service document-service fraud-service rules-service notification-service analytics-service; do
  docker build -t claim-processing/$svc:latest services/$svc/
done
```

### Step 3: Build Frontend

```bash
cd frontend
npm install
npm run build
```

### Step 4: Deploy Infrastructure

```bash
cd infra
source .venv/bin/activate

# For finch users
export CDK_DOCKER=finch

cdk deploy --all --require-approval never --profile <your-profile>
```

### Step 5: Get Application URL

```bash
aws cloudformation describe-stacks \
  --stack-name claim-processing-frontend \
  --profile <your-profile> \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`FrontendUrl`)].OutputValue' \
  --output text
```

---

## Stack Deployment Order

The CDK handles dependency ordering automatically. Stacks deploy in this sequence:

| Phase | Stacks | Duration |
|-------|--------|----------|
| 1 | NetworkStack, MonitoringStack | ~2 min |
| 2 | DatabaseStack, StorageStack | ~5 min |
| 3 | AuthServiceStack | ~2 min |
| 4 | ClaimServiceStack, FraudServiceStack, DocumentServiceStack, NotificationServiceStack, RulesServiceStack, AnalyticsServiceStack | ~3 min (parallel) |
| 5 | ApiGatewayStack | ~1 min |
| 6 | FrontendStack | ~1 min |

---

## Post-Deployment Configuration

### 1. Verify SES Email (Required for Notifications)

```bash
aws ses verify-email-identity \
  --email-address noreply@claimprocessing.com \
  --profile <your-profile>
```

**Note**: In SES sandbox mode, you must also verify recipient emails. Request production access for unrestricted sending.

### 2. Enable Bedrock Model Access (Required for Fraud Detection)

1. Go to AWS Console → Amazon Bedrock → Model access
2. Request access to **Anthropic Claude Sonnet 4.5**
3. Wait for approval (usually instant)

### 3. Create Initial Admin User

After deployment, register the first admin user via API:

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name claim-processing-api-gateway \
  --profile <your-profile> \
  --query 'Stacks[0].Outputs[?contains(OutputKey,`ApiUrl`)].OutputValue' \
  --output text)

# Register admin
curl -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "admin",
    "email": "admin@yourcompany.com",
    "password": "AdminPass123!",
    "full_name": "System Admin",
    "role": "admin"
  }'
```

### 4. Seed Assessment Rules

```bash
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "password": "AdminPass123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create a basic health claim rule
curl -X POST "$API_URL/api/rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "claim_type": "health",
    "name": "Health Auto-Approve",
    "auto_approve_threshold": 10000,
    "coverage_limit": 500000,
    "description": "Auto-approve health claims under 10000 with low fraud score"
  }'
```

### 5. Set Up Observability (CloudWatch Dashboard + Alarms)

```bash
cd scripts/stress-testing
pip install boto3 requests

# Create CloudWatch Operations Dashboard
python create_cloudwatch_dashboard.py --profile <your-profile>

# Create 42 CloudWatch Alarms
python create_cloudwatch_alarms.py --profile <your-profile>

# Verify alarms
python create_cloudwatch_alarms.py --profile <your-profile> --list
```

**Dashboard URL**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ClaimFlow-Operations

**Alarms URL**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:

### 6. (Optional) Generate Demo Claims

File a few claims through the application UI (as a Policyholder) and process them
(as an Adjudicator) to populate the platform with realistic activity for the
dashboards and analytics.

### 7. Initialize Analytics (Required)

The analytics service needs its Aurora PostgreSQL table created on first use:

```bash
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "admin", "password": "AdminPass123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST "$API_URL/api/analytics/sync" \
  -H "Authorization: Bearer $TOKEN"
```

Expected response: `{"status":"completed","records_synced":N,...}`

### 8. Fix IAM Permissions (If Needed)

If you see `AccessDeniedException` for `dynamodb:Scan` on any service, add the permission:

```bash
AWS_PROFILE=<your-profile> aws iam put-role-policy \
  --role-name <task-role-name> \
  --policy-name DynamoDBScanAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["dynamodb:Scan"],
      "Resource": ["arn:aws:dynamodb:us-east-1:<account-id>:table/claim-processing-*"]
    }]
  }'
```

---

## Teardown (Undeployment)

To completely remove all resources from AWS:

### Step 1: Empty S3 Buckets

S3 buckets must be empty before CDK can delete them:

```bash
AWS_PROFILE=<your-profile> aws s3 rm s3://claim-processing-documents-<account-id> --recursive
AWS_PROFILE=<your-profile> aws s3 rm s3://claim-processing-frontend-<account-id> --recursive
```

### Step 2: Delete ALB and Target Groups (manually created)

```bash
# Delete ALB
ALB_ARN=$(AWS_PROFILE=<your-profile> aws elbv2 describe-load-balancers --names claim-processing-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)
LISTENER_ARN=$(AWS_PROFILE=<your-profile> aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[0].ListenerArn' --output text)
AWS_PROFILE=<your-profile> aws elbv2 delete-listener --listener-arn $LISTENER_ARN
AWS_PROFILE=<your-profile> aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# Wait for ALB to be deleted
sleep 60

# Delete target groups
for TG in $(AWS_PROFILE=<your-profile> aws elbv2 describe-target-groups --query 'TargetGroups[?starts_with(TargetGroupName, `cp-`)].TargetGroupArn' --output text); do
  AWS_PROFILE=<your-profile> aws elbv2 delete-target-group --target-group-arn $TG
done
```

### Step 3: Delete CloudFront Function

```bash
ETAG=$(AWS_PROFILE=<your-profile> aws cloudfront describe-function --name claim-processing-spa-rewrite --query 'ETag' --output text)
AWS_PROFILE=<your-profile> aws cloudfront delete-function --name claim-processing-spa-rewrite --if-match $ETAG
```

### Step 4: Delete HTTP API Gateway (manually created)

```bash
AWS_PROFILE=<your-profile> aws apigatewayv2 delete-api --api-id 6oihxlw6o5
AWS_PROFILE=<your-profile> aws apigatewayv2 delete-vpc-link --vpc-link-id 2tj6cf
```

### Step 5: Delete NLB Target Groups and Listeners

```bash
NLB_ARN=$(AWS_PROFILE=<your-profile> aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(LoadBalancerName, `NLB55`)].LoadBalancerArn' --output text)
# Delete listeners
for LISTENER in $(AWS_PROFILE=<your-profile> aws elbv2 describe-listeners --load-balancer-arn $NLB_ARN --query 'Listeners[].ListenerArn' --output text); do
  AWS_PROFILE=<your-profile> aws elbv2 delete-listener --listener-arn $LISTENER
done
# Delete target group
AWS_PROFILE=<your-profile> aws elbv2 delete-target-group --target-group-arn arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/claim-auth-tg/<id>
```

### Step 6: Destroy CDK Stacks

```bash
cd infra
source .venv/bin/activate
AWS_PROFILE=<your-profile> cdk destroy --all --force
```

This will delete (in reverse dependency order):
- FrontendStack
- ApiGatewayStack
- All 7 service stacks (ECS tasks, IAM roles)
- DatabaseStack (DynamoDB tables, Aurora cluster)
- StorageStack (S3 buckets, CloudFront distributions)
- MonitoringStack (CloudWatch log groups)
- NetworkStack (VPC, subnets, NAT gateway)

### Step 7: Verify Cleanup

```bash
AWS_PROFILE=<your-profile> aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?contains(StackName, `claim-processing`)].StackName' \
  --output text
```

Should return empty (no stacks remaining).

### Estimated Teardown Time
- S3 cleanup: 1 minute
- ALB/Target Group deletion: 2 minutes
- CDK destroy: 15-20 minutes (Aurora deletion takes longest)

---

**⚠️ Warning**: Teardown deletes ALL data permanently — DynamoDB tables, Aurora database, S3 documents, and all user accounts. This action is irreversible.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `CDK bootstrap failed` | Ensure your IAM user has `AdministratorAccess` or CDK-specific permissions |
| `finch build fails` | Ensure finch VM is running: `finch vm start` |
| `ECS tasks failing health check` | Check CloudWatch logs: `/claim-processing/<service-name>` |
| `API Gateway 503` | ECS tasks may still be starting. Wait 2-3 minutes after deploy |
| `Bedrock InvokeModel denied` | Enable model access in AWS Console → Bedrock → Model access |
| `SES email not sending` | Verify sender email or request SES production access |
| `Frontend shows blank page` | Check browser console for API URL configuration errors |
| `Circular import: constructs` | Local `shared_constructs/` dir must NOT be named `constructs/` (conflicts with pip package) |
| `Cannot find version X for aurora-postgresql` | Check available versions: `aws rds describe-db-engine-versions --engine aurora-postgresql`. Use `AuroraPostgresEngineVersion.of("16.8", "16")` |
| `S3BucketOrigin not found` | CDK 2.150 uses `S3Origin` with OAI pattern, not `S3BucketOrigin.with_origin_access_control()` |
| `Cannot find asset at frontend/build` | Run `npm run build` in `frontend/` first, or create `frontend/build/index.html` manually |
| `exec format error` in ECS | Add `--platform=linux/amd64` to Dockerfiles (Apple Silicon builds ARM64 by default) |
| `Float types not supported` (DynamoDB) | Convert floats to `Decimal` in repository layer |
| `bcrypt __about__` error | Pin `bcrypt==4.0.1` in requirements.txt |
| `CloudFront returns HTML for /api/*` | Re-add `/api/*` cache behavior with ALB origin in CloudFront distribution |
| `Analytics UndefinedTable` | Run `POST /api/analytics/sync` with admin token to create Aurora table |
| `Notification AccessDenied Scan` | Add `dynamodb:Scan` to notification service task role IAM policy |
| `Datadog service shows cloudwatch` | Set `DD_FETCH_LOG_GROUP_TAGS=true` on forwarder + tag log groups with `service=claim-processing:<name>` |

---

## Architecture Reference

```
Internet → CloudFront (Frontend SPA)
         → API Gateway → VPC Link → ECS Fargate (7 services)
                                        ↓
                          DynamoDB | Aurora PG | S3
                          Bedrock | Textract | Comprehend
                          SES | SNS | QuickSight
```

**Region**: us-east-1 (single region)
**Compute**: ECS Fargate (0.5 vCPU, 1GB per service, auto-scale 1→3)
**Database**: DynamoDB (on-demand) + Aurora PostgreSQL (db.t4g.medium)
**CDN**: CloudFront for frontend and document delivery
