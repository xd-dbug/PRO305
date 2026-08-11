# Project Context

Written by Claude Code while scaffolding the Week 1 seed issues from `docs/BOARD_SETUP.md`.
Read this first if you're picking up work in this repo without prior context.

## What this project is

A 4-week course project (PRO305): an AWS-based recipe sharing platform with an
AI-powered meal planner add-on, built solo but structured as if 4 people + "you" (the
mealplan/AI owner) were each responsible for a track. See `README.md` for the full
architecture and `docs/BOARD_SETUP.md` for the board/issue setup this scaffolding
implements.

## Decisions made while scaffolding Week 1

- **IaC:** AWS SAM (`infra/template.yaml`). No Terraform. Nothing has been deployed —
  templates and code only. The AWS CLI session on this machine was expired at the time
  of writing; re-authenticate before running `sam deploy`.
- **Backend:** Python 3.13 Lambdas, one per domain (`recipes`, `auth`) using
  `aws-lambda-powertools`'s `APIGatewayRestResolver` for in-Lambda routing, plus two
  small standalone Lambdas (`infra/health`, `infra/rds_test`) that don't use Powertools.
- **Shared code:** `backend/shared/` (`db.py`, `responses.py`) is packaged as a SAM
  Lambda Layer (`SharedLayer` in `template.yaml`), not duplicated per function.
- **Frontend:** Vite + React + JavaScript (no TypeScript, no router library yet — the
  scaffold is a single `App.jsx` that calls the real API client).
- **Testing:** pytest for pure/DB-independent logic only (`shared/responses.py`,
  `auth/auth_service.py`, `recipes/app.py`'s stub routes). Anything DB-dependent
  (`auth/app.py`'s login route, `shared/db.py`, `infra/rds_test`) is smoke-tested
  manually via `sam local invoke` / `sam local start-api` after a real deploy, not by
  an automated suite — there's no live database to test against yet.

## Status per track (as of scaffolding)

- **Infra (Person C):** `infra/template.yaml` defines the API Gateway, a `/health`
  smoke test route, the RDS instance, the S3 bucket, an SNS topic, and 4 CloudWatch
  alarm stubs with placeholder thresholds (explicitly `TBD — Week 3`, per the seed
  issue). Not deployed.
- **Auth (Person B):** `backend/auth/schema.sql` (single `users` table with a `role`
  enum), `backend/auth/seed.py`, and a working `POST /auth/login` that issues a real
  JWT — but no route anywhere checks that JWT yet (enforcement is a later issue, not
  this one).
- **Recipes (Person A):** `backend/recipes/app.py` — full route skeleton (CRUD + rate
  + save), all returning mock data, no DB calls. The S3 photo bucket lives in infra's
  template since infra owns the repo's IaC.
- **Frontend (Person D):** Vite scaffold in `frontend/`, `src/api/client.js` wired to
  every route above. `docs/API_CONTRACT.md` documents the real routes (written after
  the routes existed, not guessed ahead of them).
- **Mealplan/AI (you):** deliberately untouched. Anthropic Console signup + spend cap,
  the SQS consumer Lambda skeleton, and the Claude API test call are being built
  hands-on in a follow-up session rather than generated automatically.

## Where things live

See `README.md`'s "Repo layout" section — it's accurate as of this scaffolding pass.

## What's NOT done yet

- Nothing is deployed to AWS.
- No JWT enforcement middleware.
- No real DB queries in the recipes routes.
- CloudWatch alarm thresholds are placeholders.
- The mealplan/AI track (all 3 of its seed issues).
