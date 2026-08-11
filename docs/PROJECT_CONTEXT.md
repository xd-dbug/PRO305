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
- **Shared code:** `backend/layer/shared/` (`db.py`, `responses.py`) is packaged as a SAM
  Lambda Layer (`SharedLayer` in `template.yaml`, `ContentUri: ../backend/layer/`), not
  duplicated per function. The `shared/` subfolder is required so SAM's python-pip layer
  build workflow — which copies the *contents* of `ContentUri` into `/opt/python/` — lands
  the package at `/opt/python/shared/`, matching every Lambda's `from shared.x import y`
  imports.
- **Frontend:** Vite + React + JavaScript (no TypeScript, no router library yet — the
  scaffold is a single `App.jsx` that calls the real API client).
- **Testing:** pytest for pure/DB-independent logic only (`shared/responses.py`,
  `auth/auth_service.py`, `recipes/app.py`'s stub routes). Anything DB-dependent
  (`auth/app.py`'s login route, `shared/db.py`, `infra/rds_test`) is smoke-tested
  manually against the *deployed* stack via `curl`/`aws lambda invoke` after a real
  `sam deploy`, not by an automated suite — there's no live database to test against
  yet. `sam local invoke` / `sam local start-api` do **not** work for this: the RDS
  instance is `PubliclyAccessible: false` and VPC-bound, so a local container can't
  reach it, and `VpcConfig` only affects a deployed Lambda's networking anyway. See
  `infra/README.md`'s "Manual smoke test after deploying" section for the exact
  commands.

### Running the tests

    pip install -r backend/requirements-dev.txt \
                -r backend/layer/requirements.txt \
                -r backend/auth/requirements.txt \
                -r backend/recipes/requirements.txt
    pytest backend -v

`backend/requirements-dev.txt` alone only provides `pytest` — the auth and recipes test
suites import `jwt`/`bcrypt` and `aws_lambda_powertools` respectively, which are pinned
in each function's own `requirements.txt` (not duplicated into the dev-only file, to
avoid two sources of truth for the same pins).

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
