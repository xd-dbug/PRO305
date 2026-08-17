# Project Context

Originally written by Claude Code while scaffolding the Week 1 seed issues from
`docs/BOARD_SETUP.md`; rewritten from a full re-read of the repo + GitHub issues/PRs on
2026-08-16, most recently updated 2026-08-17 after the stack's first real deploy
(commit `d21abb9` + uncommitted mealplan/infra work). Read this first if you're picking
up work in this repo without prior context — this file drifts fast in an active Week 2,
so re-verify anything load-bearing against the code before relying on it.

## What this project is

A 4-week course project (PRO305): an AWS-based recipe sharing platform with an
AI-powered meal planner add-on, built as a small team (4 named contributors show up in
git history — Damian, LissAponte, nscarbrough — plus "you," the mealplan/AI owner) each
responsible for a track. See `README.md` for the full architecture and
`docs/BOARD_SETUP.md` for the board/issue setup.

## Where things actually stand

- **The stack is deployed for real now** — first-ever `sam deploy` of this project,
  2026-08-17, stack `recipe-sharing-app` in `us-east-2`. `ApiUrl`:
  `https://yat192qddb.execute-api.us-east-2.amazonaws.com/dev/`. Schema applied by hand
  (`mysql ... < backend/{auth,recipes,mealplan}/schema.sql`, in that dependency order)
  and `backend/auth/seed.py` run against the live DB — two test users exist:
  `alice@example.com` (`user`) and `mod@example.com` (`moderator`), both
  `<name>-test-password`. `infra/samconfig.toml` now exists (gitignored, no secrets in
  it — `NoEcho` params aren't persisted there).
- **`RecipeDB` is `PubliclyAccessible: true`, not `false` — a deliberate, discussed
  tradeoff, not an oversight.** No Lambda in this stack has `VpcConfig`. Giving them
  VPC networking to reach RDS privately would cut off `MealplanFunction`'s internet
  access (needed for the Claude API call) unless a NAT Gateway got added
  (~$33/month + data, ongoing cost for a course project). Chose: RDS gets its own
  dedicated `RecipeDbSecurityGroup` (0.0.0.0/0 on 3306, not the account's shared
  default SG — this VPC has other unrelated projects in it), protection is the DB
  password alone. Revisit if this ever needs to be production-real.
- **`master` is the integration branch** (not `main` — `CONTRIBUTING.md` says `main` but
  the repo actually uses `master`; go with what's real). Latest merged work: PR #29
  (role casing fix, closes #28), PR #27 (auth enforcement, closes #7), and
  `nscarbrough`'s Week 2 recipes/S3 commit.
- **In-flight branches/worktrees as of this write-up:**
  - `feature/damian-mealplan-generate-persist` (issue #2, this repo's main checkout) —
    **all 4 tasks done**, deployed, and verified end-to-end against the real stack (see
    Mealplan status below) — still uncommitted, ready for commit/PR.
  - `.worktrees/cloudwatch-alarm-thresholds` (issue #11, branch
    `feature/damian-infra-cloudwatch-thresholds`) — Task 1 (real alarm descriptions)
    done, uncommitted. Deploy + forced-alarm verification still pending — note it's
    working off a stale copy of `infra/template.yaml` from before the `RecipeDB`
    public-access change above; rebase/re-pull before deploying from that worktree.
  - `.worktrees/auth-jwt-middleware` (branch `feature/damian-auth-jwt-middleware`) —
    this branch's PR (#27) is already merged into `master`; the worktree itself is
    stale and can be removed whenever convenient.
  - Several older local branches (`feature/damain-infra_issue`,
    `feature/damain-mealplan_issues`, `feature/damian-mealplan-sqs-consumer`) are fully
    merged/stale — safe cleanup candidates, not touched here.

## Status per track

- **Infra:** `infra/template.yaml` defines API Gateway (now with `BinaryMediaTypes` for
  multipart photo uploads), RDS (now public — see above), the S3 photo bucket, SNS,
  `MealplanQueue`, and 4 CloudWatch alarms. `Api5xxRateAlarm`/`ApiP95LatencyAlarm` have
  real descriptions now (issue #11, Task 1) but still need a deploy + forced-transition
  check to close the issue — now that the stack is actually live, this is unblocked.
  `MealplanDlqFailureRateAlarm` still points at a DLQ that doesn't exist (issue #3).
  `infra/README.md`'s "no `VpcConfig`" gap is superseded by the public-RDS decision
  above — no Lambda needs `VpcConfig` now. Still open: no `AlarmTopic` subscription
  (alarms notify nobody even once firing).
- **Auth:** `users` table (lowercase `role` enum: `'user'`/`'moderator'`),
  `POST /auth/login` issuing real JWTs — all from Week 1. Week 2 added
  `backend/layer/shared/auth_middleware.py` (issue #7, PR #27): `require_auth`,
  `require_role`, `require_owner_or_moderator`, correctly checking the lowercase role
  enum, well-tested (`backend/layer/tests/test_auth_middleware.py`). Issues #8
  (moderator permissions) and #9 (dietary preference tags CRUD) are still open — #9 is
  what blocks issue #1's dietary-tag prompting.
- **Recipes:** Full DB-backed CRUD, ratings (`POST /recipes/{id}/ratings` — note the
  route was renamed from `/rate` to `/ratings`, but `frontend/src/api/client.js` still
  calls the old `/rate` path), S3 photo upload (`s3utils.py`, `multipart_utils.py`).
  Auth is functional now (issue #28 fixed, PR #29) but still **inconsistent** — see
  Known bugs below: two separate auth implementations (`token_auth.py` and
  `shared.auth_middleware`) both work now, but only one route uses the shared one.
- **Frontend:** Still essentially unstarted despite looking otherwise. `App.jsx` (27
  lines) and `main.jsx` only; `Browser.jsx`, `Homepage.jsx`, `Login.jsx`, `Recipe.jsx`,
  `RecipeList.jsx`, `Register.jsx` all exist as 0-line empty files (CSS + filenames
  scaffolded, no content) — this is what issues #12/#13 (still open) are for.
  `src/api/client.js` is wired up but has drifted from the real API (see the
  `/rate`-vs-`/ratings` mismatch above).
- **Mealplan/AI (you):** `mealplan_job` schema in place (issue #10, closed). **Issue #2
  is fully done and verified against the real deployed stack** (this session):
  `generate.py` (`POST /mealplan/generate`, auth via `shared.auth_middleware`) inserts
  the `pending` row and enqueues SQS; the rewritten consumer (`app.py`) fetches
  `request_preferences`, calls Claude with a minimal prompt (days/mealsPerDay only —
  no dietary tags/saved recipes, that's #1), and writes `status='complete'` +
  `generated_plan` (or `status='failed'` + `error_message` on any exception, re-raising
  so #3's DLQ can still act on it). Live test: `curl POST /mealplan/generate` → `202`,
  `SELECT * FROM mealplan_job` a few seconds later showed `status='complete'` with a
  real Claude-generated 2-day plan in the documented shape. Issue #1 (dietary-tag/
  saved-recipe-aware prompting) still blocked on #9. Issue #3 (DLQ wiring) not started
  — its "job status reflects failed" verification step is unblocked now that #2's
  consumer exists and is deployed.

## Known bugs worth knowing about

1. **Auth casing bug — GitHub issue #28, fixed (PR #29, merged).**
   `backend/recipes/token_auth.py`'s `get_current_user()` used to check
   `role not in ("User", "Moderator")` (capitalized) against a lowercase
   `'user'`/`'moderator'` enum, 401ing every real JWT on recipe write routes.
   PR #29 fixed the casing in both `get_current_user()` and
   `require_owner_or_moderator()` — a minimal 4-line patch, explicitly scoped to just
   the casing (see the PR body). It deliberately did **not**:
   - migrate recipe routes to `shared.auth_middleware` (the issue's own "worth
     considering" suggestion) — `token_auth.py` and `shared.auth_middleware` remain
     two parallel, now-both-correct implementations. `backend/recipes/app.py:29-33`
     still imports `require_owner_or_moderator` from *both* modules (the second import
     silently shadows the first) and only `save_recipe` actually calls into
     `shared.auth_middleware`; `create_recipe`/`update_recipe`/`rate_recipe` still use
     the local `token_auth.get_current_user`. Both now behave correctly, so this is a
     duplication/maintenance smell rather than a live bug — but the two could drift
     again.
   - fix `backend/recipes/tests/test_recipes_routes.py`'s collection failure (see bug
     #2 below) — the PR's own description calls this pre-existing and explicitly out
     of scope.
   - This session's `backend/mealplan/generate.py` (issue #2) was switched to
     `shared.auth_middleware.require_auth` directly rather than copying
     `token_auth.py` a second time — unaffected by either version of this bug.
2. **`backend/recipes/tests/test_recipes_routes.py` doesn't collect.** Loads
   `backend/recipes/app.py` via `importlib.util.spec_from_file_location`, which executes
   `from token_auth import ...` — but nothing puts `backend/recipes/` itself on
   `sys.path` for local test runs (it works when deployed, since SAM's `CodeUri` makes a
   Lambda's own directory its import root). `backend/conftest.py` (added in PR #27)
   fixes the parallel issue for `shared.*` imports but doesn't address this. Pre-existing,
   confirmed still unfixed after PR #29 (that PR explicitly called it out-of-scope) —
   recipes' own test infra needs either a `sys.path` shim like
   `backend/mealplan/tests/test_generate.py`'s (scoped/cleaned up immediately, see next
   item for why that matters) or a proper package layout.
   - **One more issue waiting behind this one, confirmed by direct check:**
     `backend/recipes/app.py:30` does `import s3_utils`, but the file on disk is
     `backend/recipes/s3utils.py` (no underscore) — a real name mismatch that will
     throw once the `token_auth` sys.path problem above is fixed, not before.
3. **(Fixed this session) `backend/mealplan/test_claude_call.py` → renamed to
   `manual_claude_smoke_check.py`.** It matched pytest's default `test_*.py` collection
   glob despite being a manual, non-automated script (see its own docstring), which put
   `backend/mealplan` on `sys.path` for the rest of any `pytest backend` session. That
   was harmless on its own, but as soon as `backend/mealplan/token_auth.py` was added
   (this session, same name as recipes' module), it caused recipes' `app.py` to
   accidentally import mealplan's `token_auth` instead of its own — a same-name-module
   collision. Renamed to avoid *both* of pytest's default globs (`test_*.py` and
   `*_test.py`) — a name ending in `_test.py` still gets collected.

### Running the tests

    pip install -r backend/requirements-dev.txt \
                -r backend/layer/requirements.txt \
                -r backend/auth/requirements.txt \
                -r backend/recipes/requirements.txt \
                -r backend/mealplan/requirements.txt
    pytest backend -v

`backend/conftest.py` puts the shared layer on `sys.path` automatically now. `pytest
backend -v` as a whole still fails on collecting `backend/recipes/tests/` (Known bug #2
above) — run `pytest backend/auth backend/layer backend/mealplan -v` to exercise
everything that currently passes (23 tests as of this write-up). Recipes' DB-dependent
routes are still smoke-tested manually against a deployed stack, not by the automated
suite, per the original Week 1 decision.

## Where things live

See `README.md`'s "Repo layout" section. One addition since Week 1: a repo-specific
Claude Code subagent for the auth track lives at `.claude/agents/auth-agent.md`, used to
implement issue #7 (see `docs/superpowers/plans/2026-08-16-auth-agent-subagent.md`).

## What's NOT done yet

- Deployed now (`recipe-sharing-app`, `us-east-2`), but only mealplan's `/mealplan/generate`
  path has been curl-verified live; `/auth/login` was exercised as a dependency of that
  test but recipes/other routes haven't been.
- Frontend is scaffolding only; no real UI behind any `.jsx` file except `App.jsx`.
- #28 is fixed, but recipes still has two parallel auth implementations
  (`token_auth.py` and `shared.auth_middleware`) — only `save_recipe` uses the shared
  one; migrating the rest and dropping `token_auth.py` is still open work, just no
  longer a correctness bug.
- `backend/recipes/tests/test_recipes_routes.py` doesn't collect locally — and once
  that's fixed, a `s3_utils` vs `s3utils.py` import-name mismatch in `app.py` is next
  in line.
- Issue #8 (moderator permissions), #9 (dietary tags), #12/#13 (frontend UI) open.
- Mealplan: issue #2 is done and deployed. Still open: dietary-tag-aware prompting
  (#1, blocked on #9) and DLQ wiring (#3, unblocked now that #2 is live).
- CloudWatch alarms have real thresholds now (#11 Task 1) but no observed state
  transition and no `AlarmTopic` subscription — both unblocked now that the stack is
  live, still not done.
- Nothing in this session's mealplan or infra work is committed yet (deliberately —
  commits are the repo owner's to run).