# Infra — deploy instructions

This stack is defined in `template.yaml` (AWS SAM). Nothing here has been deployed —
these are templates and skeleton code only.

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

## Known gaps in this skeleton

- `RdsTestFunction` has no `VpcConfig`. RDS instances default to a VPC; a Lambda outside
  that VPC cannot reach it. Add `VpcConfig` (subnet + security group IDs) once you know
  which VPC/subnets the RDS instance landed in — these are only knowable after `RecipeDB`
  is actually created, so they can't be hardcoded here.
- The `MealplanDlqFailureRateAlarm` and `MealplanGenerationTimeAlarm` alarms reference a
  DLQ and a custom metric that don't exist yet — they'll stay in `INSUFFICIENT_DATA` until
  the mealplan track is built. This is expected.
- All 4 CloudWatch alarm thresholds are placeholders (per the seed issue: "thresholds TBD
  in Week 3"). Revisit before relying on them.

## Manual smoke test after deploying

    curl "$(aws cloudformation describe-stacks --stack-name <your-stack> \
      --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)health"
    # -> {"status": "ok"}

    sam local invoke RdsTestFunction --event <(echo '{}')
    # -> {"statusCode": 200, "body": "{\"rds_connection\": \"ok\"}"} once VpcConfig is set
