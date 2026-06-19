# sample-claimflow-devops-agent-workshop

Sample insurance claims microservices app on AWS used to demonstrate AWS DevOps Agent incident detection via fault injection.

## Overview

ClaimFlow is a sample multi-service insurance claims application built on AWS. It supports Health, Motor, Property, and Travel insurance claims with automated fraud detection (using Amazon Bedrock), document extraction, and real-time tracking. It accompanies the *Autonomous Incident Response with AWS DevOps Agent* workshop and ships with a reproducible set of fault-injection scenarios used to demonstrate how AWS DevOps Agent detects and investigates incidents.

> **This is sample code, for non-production usage.** You should work with your security and legal teams to meet your organizational security, regulatory and compliance requirements before deployment.

## Architecture

```
Frontend (React TS) → CloudFront → API Gateway → VPC Link → internal NLB → ECS Fargate (7 services)
                                                                                  │
                                  ┌───────────────────────────────────────────────┼───────────────────────────────┐
                                  │                          │                     │                               │
                             Auth Service            Claim Service          Fraud Service                  Document/Notif/Rules/Analytics
                             JWT / RBAC              Lifecycle              Amazon Bedrock                  Textract / SES+SNS / Rules / Aurora
                                  │                          │                     │
                             DynamoDB                 DynamoDB              DynamoDB + Bedrock
```

The public entry point is Amazon CloudFront in front of Amazon API Gateway. API Gateway routes `/api/*` traffic through a VPC Link to an internal (non-internet-facing) Network Load Balancer, which fronts the ECS Fargate services. The services are not directly reachable from the internet.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Compute | Amazon ECS Fargate (7 services) |
| Database | Amazon DynamoDB + Amazon Aurora PostgreSQL |
| Storage | Amazon S3 + Amazon CloudFront |
| AI/ML | Amazon Bedrock (Anthropic Claude Sonnet 4.5) |
| Document Processing | Amazon Textract + Amazon Comprehend |
| Notifications | Amazon SES (email) + Amazon SNS (SMS) |
| Routing | Amazon API Gateway + VPC Link + internal NLB + CloudFront |
| Infrastructure | AWS CDK (Python) |

## Project Structure

```
sample-claimflow-devops-agent-workshop/
├── frontend/                 # React TypeScript SPA
├── services/                 # Python FastAPI microservices
│   ├── auth-service/         # Authentication & RBAC
│   ├── claim-service/        # Claim lifecycle management
│   ├── fraud-service/        # AI fraud detection (Amazon Bedrock)
│   ├── document-service/     # Document upload & OCR
│   ├── notification-service/ # Email + SMS notifications
│   ├── rules-service/        # Assessment rules engine
│   └── analytics-service/    # Data aggregation & dashboards
├── infra/                    # AWS CDK infrastructure (Python)
├── scripts/                  # Automation + fault-injection scenarios
│   └── fault-injection/      # DevOps Agent demo fault scenarios
├── docs/                     # Additional documentation
├── deploy.sh                 # One-command deployment script
├── LICENSE                   # MIT-0
├── THIRD-PARTY-LICENSES      # Attribution for third-party dependencies
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md                 # This file
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- AWS CDK CLI (`npm install -g aws-cdk`)
- Finch or Docker (to build container images)
- AWS CLI configured with credentials for your target account
- Amazon Bedrock access to Anthropic Claude Sonnet 4.5 enabled in your account (region `us-east-1`)

### Deploy

```bash
./deploy.sh <aws-profile-name>
```

The default deployment region is `us-east-1`. Deployment provisions a VPC, Aurora PostgreSQL, DynamoDB tables, the ECS Fargate services, API Gateway, and a CloudFront distribution.

### Undeploy

```bash
cd infra
source .venv/bin/activate
AWS_PROFILE=<your-profile> cdk destroy --all
```

## Features

### Demo users

On first startup the auth-service idempotently seeds three demo accounts (gated by the `SEED_DEFAULT_USERS` environment variable, default `true`). They are intended only for short-lived demos and workshops, and the application logs them as such. Disable seeding (`SEED_DEFAULT_USERS=false`) for any longer-lived deployment, and rotate or remove these accounts before exposing the application beyond a sandbox account.

| User ID | Password | Role |
|---|---|---|
| admin | admin12345 | System Admin |
| adjudicator | Adjudicator123 | Claims Adjudicator |
| policyholder | PolicyHolder123 | Policyholder |

### Policyholder
- File claims (Health, Motor, Property, Travel)
- Upload supporting documents
- Track claim status in real time

### Claims Adjudicator
- Review pending claims, approve with settlement amount, or reject with a reason
- Initiate settlement and close claims

### System Admin
- Service health monitoring and API response-time tracking
- User management and analytics dashboard

## Fault Injection (DevOps Agent Demo)

The `scripts/fault-injection/` directory contains three reproducible fault scenarios used to demonstrate autonomous incident detection and diagnosis (for example with AWS DevOps Agent):

1. **Bad Query** — CPU burn on `claim-service`
2. **Memory Sidecar** — OOM crash loop on `fraud-service`
3. **DDoS** — HTTP flood from rogue ECS tasks

```bash
cd scripts/fault-injection

./inject.sh 1 <aws-profile>     # inject scenario 1
./recover.sh <aws-profile>      # recover between scenarios
./recover.sh <aws-profile> --verify-only   # verify clean state
```

See [scripts/fault-injection/README.md](scripts/fault-injection/README.md) for full details.

> **Warning**: The fault-injection scripts intentionally degrade the running application (high CPU, OOM, simulated DDoS). Run them only against a dedicated demo/sandbox account, never against production.

### Workshop-only configuration

The CDK stack enables a few defaults that are convenient for a demo or workshop but are not appropriate for any longer-lived environment. Review and disable them before reusing this code outside a sandbox account:

- **`enable_execute_command=True`** on the ECS services. The fault-injection scripts use `aws ecs execute-command` to inject faults into running containers. This setting opens an SSM-based shell into every task and should be set to `False` (the default for production workloads) outside a workshop sandbox.
- **`SEED_DEFAULT_USERS=true`** on the auth-service. Seeds three well-known demo accounts on first startup. Set to `false` for any deployment that will be reachable beyond your own sandbox account.
- **`removal_policy=DESTROY`** on Aurora, DynamoDB tables, and the frontend S3 bucket. Makes teardown a one-command operation. Switch to `RETAIN` (or back up first) if the data has any value.

## Documentation

- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [User Guide](docs/USER_GUIDE.md)
- [Demo Guide](docs/DEMO_GUIDE.md)
- [DevOps Agent Demo](docs/DEVOPS_AGENT_DEMO.md)
- [DevOps Agent Setup](docs/DEVOPS_AGENT_SETUP.md)

## Estimated cost

The application is intended to run only for the duration of a demo or workshop. Approximate cost in `us-east-1` while the stack is running:

| Component | Configuration | Approx. cost |
|---|---|---|
| ECS Fargate | 7 services × 0.25 vCPU + 0.5 GB, 1 task each, 24×7 | ~$11 / day |
| Amazon Aurora PostgreSQL | `db.t3.medium`, single instance, 24×7 | ~$3 / day |
| Amazon DynamoDB | On-demand, low traffic | < $0.50 / day |
| NAT Gateway | 1 NAT, 24×7 | ~$1.10 / day |
| Application Load Balancers + API Gateway | Internal NLB + API Gateway HTTP API | ~$1 / day |
| Amazon CloudFront + S3 | Demo-level traffic | < $0.50 / day |
| Amazon Bedrock (Claude Sonnet 4.5) | Pay-per-invocation; only fraud-service calls | depends on usage |
| Amazon Textract / Comprehend / SES / SNS | Pay-per-call; demo-level usage | < $0.50 / day |

**Approximate total: ~$17–20 / day** while the stack is running, plus per-call Bedrock charges (typically < $1 / day at workshop volumes).

To avoid charges between demos, run `cdk destroy --all` from the `infra/` directory. See the [Undeploy](#undeploy) section above. These figures are approximate, do not include taxes, and assume the default region (`us-east-1`); use the [AWS Pricing Calculator](https://calculator.aws/) for an authoritative estimate.

## Claim Lifecycle

```
Draft → Under Review → Approved → Settlement → Closed
                     → Rejected → Closed
```

## Security

See [CONTRIBUTING.md](CONTRIBUTING.md#security-issue-notifications) for how to report security issues. This is sample code intended for demos and learning; review and harden it before production use.

## Known limitations

This is sample code optimized for ease of reading and short-lived demo use. The following items are known and accepted in that context; harden them before any production use:

- **Dockerfile base images are not SHA-pinned.** Each `Dockerfile` uses a floating tag (for example `python:3.12-slim`) rather than `python:3.12-slim@sha256:...`. Container builds are therefore reproducible only as long as the upstream tag is stable. Pin to digests if you fork this for a longer-lived environment.
- **Some shell scripts use unquoted variable expansions.** `deploy.sh` and `scripts/fault-injection/inject.sh` interpolate variables without consistent double-quoting. The inputs are controlled (an AWS profile name and a small set of script arguments), so this is acceptable for the demo, but harden the quoting before extending the scripts to take untrusted input.
- **`pytest` `tmpdir` advisory (CVE-2025-71176).** All seven services pin a recent `pytest` for the dev/test extras. The advisory is upstream-unfixed at the time of writing (see [pytest-dev/pytest#13669](https://github.com/pytest-dev/pytest/issues/13669)) and reflects a local-privilege-escalation race against `/tmp/pytest-of-{user}` on multi-user UNIX hosts. `pytest` is a development-only dependency — it is not installed in the production container images — so the advisory does not apply to the deployed application. Run tests on a single-user workstation or CI runner to avoid the local-attacker scenario.
- **Secrets handling.** The application uses AWS Secrets Manager for the Aurora password and a runtime-generated JWT signing key. Demo user passwords are seeded at startup and intentionally well-known (see [Demo users](#demo-users)).

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
