# GitHub Projects setup

## 1. Create the board

Repo → Projects tab → New project → **Board** template.

Columns: `Backlog` → `To Do` → `In Progress` → `In Review` → `Done`

## 2. Milestones (map to your 4-week timeline)

Repo → Issues → Milestones → New milestone, one per week:

- **Week 1 — Infra kickstart & scaffolding** (RDS, API Gateway skeleton, auth scaffolding, repo structure)
- **Week 2 — Core features in parallel** (recipe CRUD, auth enforcement, meal-plan pipeline, UI against mocked API)
- **Week 3 — Integration** (wire frontend to real endpoints, alerts live, DLQ tested)
- **Week 4 — Hardening & demo prep** (bug fixes, demo script, bad-Lambda trigger rehearsal)

## 3. Labels

`recipes` `auth` `mealplan` `infra` `frontend` `bug` `blocked`

## 4. Initial issues to seed (Week 1)

Create these now so everyone has a starting point day one — assign per your existing split:

**You (mealplan/AI):**
- Set up Anthropic Console account + hard spend cap ($12)
- SQS consumer Lambda skeleton (receives message, no-op)
- Claude API integration — single test call with a hardcoded prompt

**Person A (recipes):**
- Recipe CRUD endpoint skeletons (routes only, no DB logic yet)
- S3 bucket setup for photo uploads

**Person B (auth):**
- User/Moderator table schema + seed script
- JWT issuance on login (no enforcement yet)

**Person C (infra):**
- RDS instance provisioned, connection tested from a Lambda
- API Gateway skeleton — one route wired end-to-end as a smoke test
- CloudWatch alert stubs (4 alerts, thresholds TBD in Week 3)

**Person D (frontend):**
- Scaffold React app
- Agree on API contract doc in `/docs` with backend owners before building against mocks

## 5. Why seed issues instead of just "figure it out"

An empty board on day one of a 4-week sprint means the first real work session is spent deciding what to work on instead of working. Seeding Week 1 issues removes that friction — everyone opens the board and has something concrete to claim.
