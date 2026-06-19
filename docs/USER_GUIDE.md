# User Guide — Claim Processing Services

## Overview

Claim Processing Services is an intelligent claims management platform that handles four types of insurance claims: **Health**, **Motor**, **Property**, and **Travel**. The platform provides AI-powered fraud detection, automated document extraction, and real-time claim tracking.

---

## Getting Started

### Accessing the Platform

Open the platform URL in your web browser:

**Production**: https://<your-cloudfront-domain>.cloudfront.net

You'll see the landing page with three persona cards. Click the one that matches your role.

### User Roles

| Role | Description | Access |
|------|-------------|--------|
| **Policyholder** | Insurance customer filing claims | File claims, track status, upload documents |
| **Claims Adjudicator** | Internal staff reviewing claims | Review queue, approve/reject, view fraud scores |
| **Admin** | System administrator | User management, analytics dashboard, rules configuration |

---

## Policyholder Guide

### 1. Register an Account

1. Click **Register** on the login page
2. Fill in:
   - User ID (your chosen username)
   - Email address
   - Password (minimum 8 characters)
   - Full name
   - Phone number (optional)
3. Click **Create Account**
4. You'll be logged in automatically

### 2. File a New Claim

1. From the dashboard, click **File New Claim**
2. **Select Claim Type**:
   - 🏥 **Health** — Hospitalization, OPD, wellness claims
   - 🚗 **Motor** — Accident, theft, vehicle damage
   - 🏠 **Property** — Fire, flood, burglary, natural disaster
   - ✈️ **Travel** — Trip cancellation, medical emergency, baggage loss

3. **Fill Claim Details** (varies by type):

   | Health | Motor | Property | Travel |
   |--------|-------|----------|--------|
   | Hospital name | Vehicle details | Property address | Trip details |
   | Diagnosis | Incident type | Damage type | Incident type |
   | Treatment dates | Incident location | Incident date | Incident location |
   | Bill amount | Damage description | Estimated loss | Claim amount |

4. **Upload Documents**:
   - Medical bills, discharge summaries (Health)
   - FIR copy, damage photos, repair estimates (Motor)
   - Damage photos, police report, valuation (Property)
   - Boarding passes, receipts, airline correspondence (Travel)
   
   Documents are automatically scanned using OCR — extracted data will auto-populate relevant fields.

5. **Review & Submit**:
   - Review all entered information
   - Click **Submit Claim**
   - The system performs fraud analysis and rules evaluation
   - You'll receive a claim reference number (e.g., `CLM-20250525-ABCD1234`)

### 3. Track Your Claims

1. Navigate to **My Claims** from the sidebar
2. View all your claims with current status:
   - 📝 **Draft** — Saved but not submitted
   - 📤 **Submitted** — Sent for processing
   - 🔍 **Under Review** — Being reviewed by an adjudicator
   - ✅ **Approved** — Claim approved, settlement pending
   - ❌ **Rejected** — Claim denied (reason provided)
   - 💰 **Settlement** — Payment being processed
   - ✔️ **Closed** — Fully resolved

3. Click any claim to see full details and status timeline

### 4. Notifications

You'll receive notifications via:
- **Email** — For all status changes
- **SMS** — For important updates (approval, rejection)

Manage preferences in **Profile → Notification Settings**.

---

## Claims Adjudicator Guide

### 1. Review Queue

1. Log in with your adjudicator credentials
2. The dashboard shows your **pending review queue**
3. Claims are sorted by submission date (oldest first)
4. High fraud-risk claims appear at the top with a warning indicator

### 2. Reviewing a Claim

1. Click a claim from the queue
2. You'll see:
   - **Claim details** — Type, amount, description, documents
   - **Fraud Risk Score** — AI-generated score (0-100):
     - 🟢 **0-30**: Low risk
     - 🟡 **31-69**: Medium risk — verify documentation
     - 🔴 **70-100**: High risk — thorough review recommended
   - **Fraud Explanation** — AI reasoning for the score
   - **Extracted Document Data** — OCR results from uploaded documents
   - **Status Timeline** — Full history of the claim

### 3. Approving a Claim

1. After review, click **Approve Claim**
2. Enter the **settlement amount** (may differ from claimed amount)
3. Add optional notes
4. Click **Confirm Approval**
5. The policyholder is notified automatically

### 4. Rejecting a Claim

1. Click **Reject Claim**
2. Enter a **rejection reason** (required, minimum 10 characters)
3. Click **Confirm Rejection**
4. The policyholder is notified with the reason

### 5. Auto-Approved Claims

Some claims are automatically approved by the rules engine:
- Low fraud score (< 30)
- Amount below auto-approve threshold
- All policy criteria met

These appear in the **Auto-Approved** section for your awareness.

---

## Admin Guide

### 1. User Management

Navigate to **Admin → Users**:

- **View all users** — See all registered users with roles and status
- **Change role** — Promote a user to Adjudicator or Admin
- **Deactivate user** — Disable an account (cannot deactivate the last admin)
- **Filter** — By role (Policyholder, Adjudicator, Admin) or status (Active, Inactive)

### 2. Analytics Dashboard

Navigate to **Admin → Analytics**:

The QuickSight-powered dashboard shows:
- **Claims Volume** — Total claims by type and time period
- **Processing Times** — Average time from submission to resolution
- **Approval Rate** — Percentage of claims approved vs rejected
- **Fraud Detection** — Fraud score distribution and flagged claims
- **Operational Health** — Service performance metrics

Use filters to drill down by:
- Date range (start date / end date)
- Claim type (Health, Motor, Property, Travel)
- Status

### 3. Claim Lifecycle Simulation

On the Admin Dashboard, click **"🎬 Simulate Claim Lifecycle"** to:
- Automatically create a random claim
- Submit it for review
- Approve or reject it (70/30 probability)
- Process settlement and close

This is useful for populating the system with realistic data for demos.

### 4. Service Health Monitoring

The Admin Dashboard shows real-time health of all 7 microservices:
- Health checks run every 60 seconds
- Green dot = healthy, Red dot = unhealthy
- Response time in milliseconds per service
- Active user count

### 5. CloudWatch Observability

**Dashboard**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ClaimFlow-Operations

**42 Alarms** monitoring:
- ECS CPU/Memory per service (threshold: 80%)
- DynamoDB throttling per table
- ALB latency and error rates
- CloudFront error rates
- NAT Gateway traffic

### 3. Rules Configuration

Assessment rules control automated claim decisions:

| Rule Parameter | Description |
|----------------|-------------|
| `auto_approve_threshold` | Claims below this amount can be auto-approved |
| `coverage_limit` | Maximum claimable amount per policy type |
| `fraud_score_threshold` | Score above this triggers manual review (default: 70) |

To manage rules:
1. Navigate to **Admin → Rules** (via API)
2. Create rules per claim type
3. Rules are evaluated automatically during claim submission

---

## Claim Lifecycle Flow

```
Policyholder                    System                      Adjudicator
     |                            |                              |
     |--- File Claim (Draft) ---->|                              |
     |                            |                              |
     |--- Submit Claim ---------->|                              |
     |                            |--- Fraud Detection (AI) ---->|
     |                            |--- Rules Evaluation -------->|
     |                            |                              |
     |                            |--- Auto-Approve? ----------->|
     |                            |        YES → Approved        |
     |                            |        NO → Under Review --->|
     |                            |                              |
     |                            |                    Review --->|
     |                            |                              |
     |<-- Notification -----------|<--- Approve/Reject ----------|
     |                            |                              |
     |--- View Status ----------->|                              |
     |                            |                              |
```

---

## Supported Document Types

| Format | Max Size | OCR Support |
|--------|----------|:-----------:|
| PDF | 10 MB | ✅ |
| JPEG/JPG | 5 MB | ✅ |
| PNG | 5 MB | ✅ |
| TIFF | 10 MB | ✅ |

Documents are processed by Amazon Textract (text extraction) and Amazon Comprehend (entity recognition) to auto-populate claim fields.

---

## FAQ

**Q: How long does claim processing take?**
A: Simple claims with low fraud risk can be auto-approved within seconds. Claims requiring manual review typically take 1-2 business days.

**Q: What if my claim is rejected?**
A: You'll receive a notification with the rejection reason. Review the reason and contact support if you believe it was incorrect.

**Q: Can I edit a submitted claim?**
A: No. Only claims in **Draft** status can be edited. Once submitted, the claim enters the review pipeline.

**Q: How is the fraud score calculated?**
A: Amazon Bedrock (Claude Sonnet 4.5) analyzes claim patterns, document consistency, historical data, and anomaly indicators to generate a risk score.

**Q: What notifications will I receive?**
A: Email and SMS notifications for: claim submitted, under review, approved, rejected, and settlement updates.

**Q: How do I reset my password?**
A: Click "Forgot Password" on the login page. Enter your email to receive a reset link (valid for 1 hour).
