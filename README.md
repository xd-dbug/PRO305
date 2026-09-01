# Recipe Sharing + AI Meal Planner

Cloud platform course project — AWS-based recipe sharing platform with an AI-powered meal planner feature.

## Architecture

- **Compute:** AWS Lambda (all functions), API Gateway (REST entry point)
- **Async pipeline:** API Gateway → SQS → Lambda consumer → Claude API → RDS
- **Storage:** RDS (MySQL) for relational data, S3 for recipe photos
- **AI:** Claude Sonnet via Anthropic API, $10–12 hard spend cap
- **Auth:** User / Moderator roles, manually seeded
- **Monitoring:** CloudWatch + SNS — API 5xx rate, meal-plan DLQ failure rate, API Gateway p95 latency, meal-plan generation time

## Repo layout

```
/backend
  /recipes        # CRUD, ratings, saved recipes (Person A)
  /auth            # registration, login, JWT, role enforcement (Person B)
  /mealplan        # SQS consumer, Claude API integration (you)
  /layer/shared    # shared utils, DB models, common Lambda layer code
/infra             # IaC — CloudFormation/SAM/Terraform, RDS provisioning, alerts (Person C)
/frontend          # UI (Person D)
/docs              # architecture diagram, proposal doc, ADRs
```

**Why one repo, not four:** at 4 people over 4 weeks, the coordination cost of syncing versions/interfaces across separate repos is higher than the cost of occasional merge conflicts in one. You lose almost nothing by monorepo-ing this, and you gain a single source of truth for the API contract between frontend and backend.

## Local setup

1. Clone the repo, create a virtualenv for `/backend` and `/infra`
2. Copy `.env.example` → `.env`, fill in RDS connection string, S3 bucket, Anthropic API key (never commit `.env`)
3. `cd frontend && npm install`
4. See `/infra/README.md` for deploying the SAM/CloudFormation stack

## Branching

- `master` — always deployable
- `feature/<person>-<short-desc>` — e.g. `feature/mealplan-sqs-consumer`
- Open a PR into `master`, at least one teammate review before merge
- No direct pushes to `master`

## Board

Tracked on GitHub Projects (see `/docs/BOARD_SETUP.md`), not Jira — issues link directly to PRs/commits.
