# Infra — deploy instructions

This stack is defined in `template.yaml` (AWS SAM) and is deployed — this isn't a
skeleton-only stack anymore.

## Prerequisites

- AWS CLI configured with credentials for the target account (`aws sso login` or
  `aws configure`)
- SAM CLI installed (already present on this machine: `sam --version`)

## Build

    cd infra
    sam build

`sam build` requires the code directories referenced by each function's `CodeUri` to
exist. `HealthFunction` and `RdsTestFunction` build standalone; `AuthFunction` and
`RecipesFunction` (added in later tasks) build once their respective `backend/`
directories exist.

## Deploy

    sam deploy --guided

You'll be prompted for:
- `DBPassword` — a new master password for the RDS instance (never commit this)
- `JWTSecret` — a random secret used to sign JWTs (generate with e.g.
  `openssl rand -hex 32`)

`sam deploy --guided` writes your answers to `samconfig.toml`, which is gitignored.

## Current state

- No Lambda in this stack has `VpcConfig`, and that's deliberate, not a gap: the mealplan
  consumer needs public internet access to reach the Claude API, and the default VPC has
  no NAT gateway. Instead, `RecipeDB` is `PubliclyAccessible: true`, reachable from
  anywhere via `RecipeDbSecurityGroup` (open on 3306), protected by the DB password alone
  rather than network isolation. `RecipeDB` also has `DeletionProtection: true`.
- `AlarmTopic` has a live email subscription (`AlarmTopicEmailSubscription`, to
  `damian.swiney1@gmail.com`) — alarm notifications are delivered, not just configured.
- The CloudWatch alarms' `ApiName` dimension matches `RecipeApi`'s explicit
  `Name: recipe-sharing-api`.
- `MealplanDLQ` and the `GenerationDurationMs` custom metric (namespace
  `RecipeSharing/Mealplan`, emitted by the mealplan consumer Lambda) both exist and are
  wired up — `MealplanDlqFailureRateAlarm` and `MealplanGenerationTimeAlarm` have real
  data to alarm on, not just `INSUFFICIENT_DATA`.
- All 4 CloudWatch alarm thresholds are real, not placeholders: 5xx rate ≥1 in 5 min, p95
  latency ≥1000ms, any DLQ message, and generation time ≥5000ms (a deliberately low
  early-warning threshold, well under the consumer Lambda's 90s timeout).
- `backend/mealplan/app.py` and `backend/mealplan/generate.py` are named the opposite of
  what you'd guess from `template.yaml`: `app.py` is the SQS consumer that calls Claude
  (`MealplanFunction`, `Handler: app.lambda_handler`), and `generate.py` is the API
  Gateway handler for `POST /mealplan/generate` and `GET /mealplan/status/{job_id}`
  (`MealplanGenerateFunction`, `Handler: generate.lambda_handler`). The wiring is correct
  and not a bug — just double-check which file you're in before editing either one.
- All 6 functions' log groups have `RetentionInDays: 14` set via
  `aws logs put-retention-policy` — logs no longer retain forever by default. This is
  *not* CloudFormation-managed: every function except `RdsTestFunction` already had an
  auto-created log group from prior invocations before this was set, and CloudFormation's
  early validation (`AWS::EarlyValidation::ResourceExistenceCheck`) refuses to add a
  `AWS::Logs::LogGroup` resource for a physical name that already exists unmanaged —
  it needs a `resources-to-import` IMPORT changeset to adopt them properly, not a normal
  `Add`. Until that's done, retention is applied operationally and could drift on a stack
  replacement or manual console change.

## Manual smoke test after deploying

    curl "$(aws cloudformation describe-stacks --stack-name <your-stack> \
      --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)health"
    # -> {"status": "ok"}

    aws lambda invoke --function-name <RdsTestFunction's deployed name> /dev/stdout
    # -> {"statusCode": 200, "body": "{\"rds_connection\": \"ok\"}"}

`sam local invoke` is not a great substitute for the above: it runs a container on your
own machine, and against an undeployed stack it can't resolve
`!GetAtt RecipeDB.Endpoint.Address`, so `DB_HOST` would be empty. Since `RecipeDB` is
`PubliclyAccessible: true`, a local machine *can* reach it directly if you pass `DB_HOST`
yourself — but `aws lambda invoke` against the real deployed function is simpler and
matches what actually runs in prod.

## Demo: forcing a mealplan failure (DLQ + alarm rehearsal)

`POST /mealplan/generate` accepts an optional `preferences.forceFailure: true` flag. The
mealplan consumer (`backend/mealplan/app.py`) checks it first, before calling Claude, and
raises immediately — so a forced failure costs no Anthropic spend and fails the same way
on all 3 SQS delivery attempts.

    curl -X POST "$API_URL/mealplan/generate" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"preferences": {"days": 1, "mealsPerDay": 1, "forceFailure": true}}'

Timing to plan a demo/rehearsal around: `MealplanQueue`'s `VisibilityTimeout` is 120s and
`maxReceiveCount` is 3, so the message is retried twice more (each after a 120s wait) before
landing in `MealplanDLQ` — roughly 4 minutes from request to DLQ arrival and
`MealplanDlqFailureRateAlarm` firing. `GET /mealplan/status/{job_id}` will show `"failed"`
immediately after the *first* attempt, well before the DLQ alarm fires — don't mistake that
for the mechanism being done early.

This flag only fails the caller's own job (no cross-user effect) and is fully reversible —
just don't set it on a real request.
