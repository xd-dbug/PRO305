# Project Context

Originally written by Claude Code while scaffolding the Week 1 seed issues from
`docs/BOARD_SETUP.md`; rewritten from a full re-read of the repo + GitHub issues/PRs on
2026-08-16, and rewritten again on 2026-09-01 during Week 4 (hardening/demo prep) —
the Week 2 version was badly stale by then (e.g. it described the frontend as
"essentially unstarted," which was no longer true). Read this first if you're picking up
work in this repo without prior context — this file still drifts fast in an active
project, so re-verify anything load-bearing against the code before relying on it.

## What this project is

A 4-week course project (PRO305): an AWS-based recipe sharing platform with an
AI-powered meal planner add-on, built as a small team (4 named contributors show up in
git history — Damian, LissAponte, nscarbrough — plus "you," the mealplan/AI owner) each
responsible for a track. See `README.md` for the full architecture and
`docs/BOARD_SETUP.md` for the board/issue setup.

## Where things actually stand (Week 4, 2026-09-01)

- **The stack has been live since Week 2** and has been through several rounds of
  hardening since. Stack `recipe-sharing-app`, `us-east-2`. Schema applied by hand
  (`mysql ... < backend/{auth,recipes,mealplan}/schema.sql`) and `backend/auth/seed.py`
  run against the live DB — `alice@example.com` (`user`) and `mod@example.com`
  (`moderator`) both exist, `<name>-test-password`. See `infra/README.md` for deploy
  mechanics and current state; that file is kept up to date operationally and is more
  reliable than this one for infra specifics.
- **`RecipeDB` is `PubliclyAccessible: true`, not `false` — a deliberate, discussed
  tradeoff, not an oversight**, and now also has `DeletionProtection: true`. No Lambda
  in this stack has `VpcConfig` (see `infra/README.md`'s "Current state" section for the
  full rationale — giving Lambdas VPC networking would cut `MealplanFunction`'s internet
  access to the Claude API without adding a NAT Gateway).
- **`master` is the integration branch** (not `main` — go with what's real; see the
  "Branching" section fix in `README.md`, which used to say `main`).
- **A dozen `.worktrees/*` directories and their branches are stale** — all already
  merged to `master`, left over from earlier Week 3 work-in-progress. Safe cleanup
  candidates (`git worktree remove` + `git branch -d`) whenever someone wants to do the
  housekeeping; not touched as part of this doc sweep since deleting branches wasn't
  in scope here.
- **All 4 original tracks (recipes, auth, mealplan/AI, infra/frontend) are functionally
  complete** — every Week 1–3 milestone issue and all but a handful of Week 4 hardening
  issues are closed. See `docs/CONTRACT_MISMATCH_LOG.md` for the specific frontend/
  backend/contract mismatches that surfaced during Week 3 integration and how each was
  fixed.

## Status per track

- **Infra:** `infra/template.yaml` defines API Gateway (`BinaryMediaTypes` for multipart
  photo uploads), public RDS, the S3 photo bucket, SNS with a live email subscription,
  `MealplanQueue` + `MealplanDLQ` (redrive after 3 attempts), and all 4 CloudWatch
  alarms with real thresholds and descriptions — see `infra/README.md`'s "Current
  state" section, which is the authoritative source for this track now. Log retention
  is set operationally (not CFN-managed — see that file for why).
- **Auth:** `users` table (lowercase `role` enum), `POST /auth/register` and
  `POST /auth/login` both implemented and returning `userId`/`role` per the contract,
  `GET`/`PUT /users/me/preferences` for dietary tags (issue #9). Role enforcement
  (issue #8) fixed and consistent — `backend/recipes/app.py` is fully migrated onto the
  shared `backend/layer/shared/auth_middleware.py` (`require_auth`,
  `require_owner_or_moderator`); the old recipes-local `token_auth.py` no longer exists.
  Photo upload uses the same `require_owner_or_moderator` check as PUT/DELETE (issue
  #71). Frontend now stores `role` from login so moderator-only UI actually shows for a
  moderator viewing someone else's recipe.
- **Recipes:** Full DB-backed CRUD, ratings at `POST /recipes/{id}/ratings` (frontend
  and backend agree on `/ratings`, not `/rate` — the old mismatch is gone), S3 photo
  upload (`backend/recipes/s3_utils.py` — correctly named, no more `s3utils.py`
  mismatch), saved recipes (`saved_recipe` table, `POST`/`DELETE /recipes/{id}/save`,
  `GET /recipes/saved`, issue #78), `avgRating` returns `null` (not `0`) when unrated.
  `servings`/`prepTime`/`cookTime`/`notes` are collected end-to-end, not silently
  dropped.
- **Frontend:** Real UI behind every route — `Browser.jsx`, `Homepage.jsx`,
  `Login.jsx`/`Register.jsx`, `Recipe.jsx`, `RecipeList.jsx`, `RecipeCreate.jsx`,
  `MealPlan.jsx`, `SavedRecipes.jsx`, `Nav.jsx`, `NotFound.jsx`, plus a global
  `ErrorBoundary.jsx`. `MealPlan.jsx` collects dietary preferences (issue #77) and has a
  "Save as recipe" flow that pre-fills `RecipeCreate.jsx` from a generated meal.
- **Mealplan/AI:** `POST /mealplan/generate` enqueues to SQS and returns immediately;
  the consumer (physically `backend/mealplan/app.py` — see the naming note in
  `infra/README.md`) builds its prompt from live dietary tags and saved recipes (issue
  #1), asks Claude for a full cookable recipe per meal (not just a name), and writes
  `status='complete'` + `generated_plan`, or `status='failed'` + `error_message` on any
  exception (re-raising so the DLQ can act on it). `MealplanFunction`'s timeout is 90s
  (bumped from the 10s default, issue #79) to give a large 7-day×3-meal plan room to
  generate. A demo-safe fault-injection flag (`preferences.forceFailure`) now exists for
  rehearsing the DLQ/alarm path on demand — see `infra/README.md`.

## Known bugs worth knowing about

All of the Week 2–era known bugs in earlier versions of this doc are fixed: the auth
role-casing bug (#28), the two-parallel-auth-implementations smell (`token_auth.py` is
gone), the `s3utils.py`/`s3_utils.py` name mismatch, and `backend/recipes/tests/`
failing to collect. `pytest backend -v` collects and passes cleanly now (75 tests as of
this write-up) — no more need to exclude `backend/recipes` from a full test run.

Nothing is tracked here as a live known bug as of this write-up. Check
`gh issue list --state open` for what's actually still open — mostly Week 4 hardening
tasks (demo rehearsal, docs, AWS cost cleanup), not correctness bugs.

### Running the tests

    pip install -r backend/requirements-dev.txt \
                -r backend/layer/requirements.txt \
                -r backend/auth/requirements.txt \
                -r backend/recipes/requirements.txt \
                -r backend/mealplan/requirements.txt
    pytest backend -v

`backend/conftest.py` puts the shared layer on `sys.path` automatically. The full suite
collects and passes now — no exclusions needed. Recipes' DB-dependent routes are still
smoke-tested manually against the deployed stack in addition to the unit suite, per the
original Week 1 decision.

## Where things live

See `README.md`'s "Repo layout" section (note: it says `/backend/shared`, but the real
path is `/backend/layer/shared`, per SAM's Lambda-layer convention — fixed as part of
this doc sweep). A repo-specific Claude Code subagent for the auth track lives at
`.claude/agents/auth-agent.md`, used to implement issue #7 (see
`docs/superpowers/plans/2026-08-16-auth-agent-subagent.md`).

## What's left

As of 2026-09-01, only Week 4 hardening/demo-prep issues remain open — no known
functional gaps in any of the four tracks. Open issues are demo rehearsal (#63, blocked
on #67 which is now done), docs (#65, this sweep — in progress), AWS cost/resource
cleanup (#74), and manual demo-readiness checks (#68, #72, #73, #75). See the GitHub
Project board (`docs/BOARD_SETUP.md`) for the current, authoritative list rather than
trusting this doc's issue numbers to stay accurate.