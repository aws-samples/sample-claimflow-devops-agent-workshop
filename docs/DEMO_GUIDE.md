# Demo Guide — Claim Processing Services

## End-to-End Claim Lifecycle Demo

This guide walks through the complete claim journey from filing to settlement, demonstrating all three personas.

**Platform URL**: https://<your-cloudfront-domain>.cloudfront.net

---

## Test Accounts

| Persona | Login URL | User ID | Password |
|---------|-----------|---------|----------|
| Policyholder | `/login/policyholder` | `testuser2` | `REDACTED-TEST-VALUE` |
| Claims Adjudicator | `/login/adjudicator` | `adjudicator1` | `REDACTED-TEST-VALUE` |
| System Admin | `/login/admin` | `admin1` | `Admin12345` |

---

## Claim Lifecycle Flow

```
┌──────────┐    ┌───────────┐    ┌──────────────┐    ┌──────────┐    ┌────────────┐    ┌────────┐
│  DRAFT   │───▶│ SUBMITTED │───▶│ UNDER REVIEW │───▶│ APPROVED │───▶│ SETTLEMENT │───▶│ CLOSED │
└──────────┘    └───────────┘    └──────────────┘    └──────────┘    └────────────┘    └────────┘
                                         │                                                    ▲
                                         │           ┌──────────┐                             │
                                         └──────────▶│ REJECTED │─────────────────────────────┘
                                                     └──────────┘
```

| Status | Who Acts | Action |
|--------|----------|--------|
| Draft | Policyholder | Creates claim, fills details |
| Submitted/Under Review | System | Auto-transitions on submit |
| Approved | Adjudicator | Reviews and approves with settlement amount |
| Rejected | Adjudicator | Reviews and rejects with reason |
| Settlement | Adjudicator | Initiates payment processing |
| Closed | Adjudicator | Finalizes the claim |

---

## Demo Script (Step by Step)

### Act 1: Policyholder Files a Claim

1. **Open the platform**: https://<your-cloudfront-domain>.cloudfront.net
2. **Show the Landing Page** — Three persona cards (Policyholder, Adjudicator, Admin)
3. **Click "Policyholder"** → Blue-themed login page
4. **Login** with `testuser2` / `REDACTED-TEST-VALUE`
5. **Dashboard** shows "My Claims" with stats and recent claims
6. **Click "File New Claim"** button
7. **Step 1 - Select Type**: Choose "Health Insurance" 🏥
8. **Step 2 - Details**:
   - Amount: `75000` (₹75,000)
   - Policy Number: `POL-HEALTH-2024-001`
   - Incident Date: Select today's date
   - Description: `Hospitalization for acute appendicitis surgery at Apollo Hospital, Mumbai. 3-day stay including surgery, post-operative care, and medications.`
9. **Step 3 - Documents**: Select a file (optional) or skip
10. **Step 4 - Review**: Verify all details, click **"Submit Claim"**
11. **Result**: Claim is created and submitted → Status moves to "Under Review"
12. **Navigate to Claims list** — See the new claim with "Under Review" status
13. **Click the claim** — See the Claim Journey timeline showing progress
14. **Logout** (top-right corner)

### Act 2: Adjudicator Reviews and Approves

1. **Go back to Landing Page**: https://<your-cloudfront-domain>.cloudfront.net
2. **Click "Claims Adjudicator"** → Green-themed login page
3. **Login** with `adjudicator1` / `REDACTED-TEST-VALUE`
4. **Dashboard** shows "Claims Queue" with all claims including the new one
5. **Click the health claim** just submitted
6. **Show the Claim Journey** — Currently at "Under Review" step
7. **Show action buttons**: "Approve" and "Reject" are available
8. **Click "Approve"** → Modal appears
9. **Enter Settlement Amount**: `70000` (₹70,000 — slightly less than claimed)
10. **Add Notes**: `Approved after verification. Settlement amount adjusted per policy terms.`
11. **Click "Confirm Approval"**
12. **Result**: Status moves to "Approved" → Timeline updates
13. **Click "Initiate Settlement"** button (now visible)
14. **Result**: Status moves to "Settlement"
15. **Click "Close Claim"** button
16. **Result**: Status moves to "Closed" → Full lifecycle complete!
17. **Show the Claim History** section — All status changes with timestamps

### Act 3: Admin Monitors the System

1. **Go back to Landing Page**
2. **Click "System Admin"** → Purple-themed login page
3. **Login** with `admin1` / `Admin12345`
4. **Dashboard** shows system overview with stats
5. **Navigate to "Analytics"** — Show charts with real data:
   - Claims by Type (bar chart)
   - Status Distribution (donut chart)
   - Monthly Trend (vertical bars)
   - Performance table
6. **Navigate to "Users"** — Show user management:
   - All registered users with roles
   - Filter by role
   - "Add User" button (creates new users)
   - "Edit" button (change roles)
   - "Deactivate" button
7. **Navigate to "Claims"** — Admin can see all claims across all users

### Act 4: Rejection Flow (Optional)

1. **As Policyholder**: File another claim (e.g., Motor Insurance, ₹2,00,000)
2. **As Adjudicator**: Open the claim → Click "Reject"
3. **Enter reason**: `Claim amount exceeds policy coverage limit. Please resubmit with correct documentation.`
4. **Click "Confirm Rejection"**
5. **Result**: Status moves to "Rejected"
6. **Click "Close Claim"** → Status moves to "Closed"
7. **As Policyholder**: Login and see the rejected claim with reason displayed

---

## Key Demo Talking Points

### Business Value
- "80% of straightforward claims settled within 24 hours"
- "70% automation rate — minimal manual intervention"
- "Real-time visibility for policyholders — no more calling support"

### Technical Highlights
- "7 microservices on AWS ECS Fargate — independently scalable"
- "React TypeScript frontend on CloudFront — global CDN delivery"
- "DynamoDB for operational data — millisecond response times"
- "Role-based access control — each persona sees only what they need"
- "Full audit trail — every status change is logged with timestamp"

### Architecture
- "Python FastAPI microservices — modern, async, high-performance"
- "AWS CDK Infrastructure as Code — 13 stacks, fully reproducible"
- "Service discovery via AWS Cloud Map — no hardcoded URLs"
- "Designed for AI integration — Amazon Bedrock for fraud detection (ready to enable)"

---

## Troubleshooting During Demo

| Issue | Quick Fix |
|-------|-----------|
| Login fails | Check credentials above, try registering a new user |
| Claim submit shows error | Ensure description is 10+ characters |
| Adjudicator sees no claims | Claims must be submitted (not just draft) |
| Page shows blank after action | Hard refresh (Cmd+Shift+R) |
| API timeout | Wait 5 seconds and retry — ECS cold start |
| Analytics "UndefinedTable" error | Run: `curl -X POST .../api/analytics/sync -H "Authorization: Bearer $TOKEN"` |
| CloudFront returns HTML for API | Re-add `/api/*` cache behavior pointing to `alb-api` origin |
| Notification "AccessDenied" on Scan | Already fixed — IAM inline policy added to task role |
| Datadog shows `service:cloudwatch` | Log group tags set — wait for new logs (old ones keep old tag) |

---

## Post-Demo Q&A Answers

**Q: How does fraud detection work?**
A: Amazon Bedrock (Claude Sonnet 4.5) analyzes claim patterns, document consistency, and historical data. Currently in demo mode — ready to enable with Bedrock model access.

**Q: How does document OCR work?**
A: Amazon Textract extracts text, Amazon Comprehend identifies entities (names, dates, amounts). Auto-populates claim fields. Document service is deployed and connected.

**Q: What about notifications?**
A: Email (SES) and SMS (SNS) notifications are configured. Notification service is deployed — requires SES domain verification for production use.

**Q: Can this scale?**
A: ECS Fargate auto-scales 1→3 tasks per service. DynamoDB on-demand scales automatically. Designed for 1,000+ claims/day at current config, easily scalable to 100K+.

---

## Act 5: DevOps Agent Demo (Stress Testing)

### Setup
```bash
cd scripts/stress-testing
pip install boto3 requests
```

### Show Healthy State
1. Login as Admin → Dashboard shows all services 🟢 Healthy
2. Open CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ClaimFlow-Operations
3. Show all metrics are flat/normal
4. Show CloudWatch Alarms: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2: — all 🟢 OK

### Inject Stress
```bash
# Option 1: API flood (causes CPU spikes)
python stress_api.py --profile my-profile --duration 120 --rps 50

# Option 2: Kill services (causes outages)
python stress_ecs.py --profile my-profile --action scale-down

# Option 3: Combined chaos
python stress_all.py --profile my-profile --level medium --duration 180
```

### Observe Degradation
1. Admin Dashboard → Services go 🔴 Unhealthy, response times spike
2. CloudWatch Dashboard → CPU/Memory graphs spike, error counts increase
3. CloudWatch Alarms → Multiple alarms fire 🔴 (HighCPU, 5xxErrors, UnhealthyTargets)
4. **DevOps Agent identifies**: "ECS CPU at 95%, 3 services unhealthy, DynamoDB throttling detected"

### Recovery
```bash
python recover_all.py --profile my-profile
```

### Verify Recovery
1. Admin Dashboard → All services return to 🟢 Healthy
2. CloudWatch Alarms → Return to 🟢 OK
3. **DevOps Agent confirms**: "All services recovered, metrics normalized"

### Key Talking Points
- "42 CloudWatch alarms monitoring every layer of the stack"
- "Automated detection of CPU spikes, memory pressure, throttling, and service outages"
- "DevOps Agent can identify root cause across multiple services simultaneously"
- "One-command recovery restores full platform health"
