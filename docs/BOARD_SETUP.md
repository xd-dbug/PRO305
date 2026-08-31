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

## 5. Week 2 issues

Week 2 is the highest integration-risk week — recipe CRUD, auth enforcement, the meal-plan pipeline, and frontend-against-mocks all run in parallel. Dependencies are marked explicitly; don't let them slip.

**You (mealplan/AI):**
- SQS consumer: parse message, build prompt from user's dietary tags + saved recipes, call Claude API
- Persist generated meal plan to RDS, mark job status (pending/complete/failed)
- DLQ wiring — route to DLQ after 2–3 failed attempts
- *Blocked by:* RDS schema for meal plans (Person C), dietary preference tags (Person B)

**Person A (recipes):**
- Recipe CRUD — full DB logic (create/read/update/delete)
- Ratings endpoint (create/read, tied to recipe + user)
- S3 photo upload — actual upload flow
- *Blocks:* nothing structurally, but finalize recipe schema early — mealplan queries against it

**Person B (auth):**
- Auth enforcement — middleware checking JWT + role on protected routes
- Moderator permissions enforced, not just documented
- Dietary preference tags — CRUD on user profile
- *Blocks:* mealplan prompt-building (needs dietary tag data)

**Person C (infra):**
- Finalize meal-plan RDS schema — priority Monday, not Friday
- Two of four CloudWatch alerts live with real thresholds: API 5xx rate, p95 latency
- *Blocks:* mealplan persistence work

**Person D (frontend):**
- Recipe list/detail/create UI against mocked data
- Meal-plan request UI + polling for async status (mock pending/complete states)
- **Do not start until the API contract doc (`/docs/API_CONTRACT.md`) is signed off by backend owners**

## 6. Week 3 issues

Week 3 is where Week 2's assumptions get tested against reality — frontend hits real endpoints for the first time. Budget the first day or two for contract drift, not new feature work. **Decide who owns tracking contract mismatches as they surface** (recommend: whoever finds it tags a "blocked" issue to the owning backend person, rather than silently patching around it client-side) — otherwise you lose the paper trail of what changed and why.

**You (mealplan/AI):**
- Wire frontend's real polling calls to `/mealplan/status/{jobId}` — confirm response shape matches contract exactly, fix drift
- Deliberately trigger DLQ failures (bad prompt, malformed message, forced timeout) and confirm messages land in the DLQ after 2–3 attempts — verify, don't assume it works because it's wired
- Meal-plan generation time alert — real threshold, not a stub
- *Blocked by:* Person C's alert infra being live enough to attach a real metric to

**Person A (recipes):**
- Swap frontend's mocked recipe/rating data for real endpoint calls, fix shape mismatches found
- Sanity-check pagination with real data volume past page 1, not just 3 mock recipes on page 1

**Person B (auth):**
- End-to-end auth check: unauthenticated requests get 401'd on every protected route, not just the ones tested in Week 2
- Moderator permission edge cases — enforced server-side, not just hidden client-side (client-side-only enforcement is a real vulnerability)

**Person C (infra):**
- Remaining two CloudWatch alerts live with real thresholds: meal-plan DLQ failure rate, meal-plan generation time
- SNS notification actually delivers somewhere checkable (email/Slack) — an alert firing into the void isn't demo-able
- *Blocks:* your DLQ alert and generation-time alert work

**Person D (frontend):**
- Replace all remaining mocked calls with real endpoints across recipe, auth, and meal-plan flows
- Handle real error states from the contract's error shape (401/403/404/500), not just happy-path UI
- Flag every contract mismatch as a "blocked" issue tagged to the owning backend person

## 7. Why seed issues instead of just "figure it out"

An empty board on day one of a 4-week sprint means the first real work session is spent deciding what to work on instead of working. Seeding Week 1 issues removes that friction — everyone opens the board and has something concrete to claim.
