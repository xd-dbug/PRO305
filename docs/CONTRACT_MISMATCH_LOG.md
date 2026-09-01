# Week 3 contract-mismatch log

What changed and why, for the writeup/rubric. There's no single tracked issue list for
this — these are pulled from `docs/RECIPES_WEEK2_NOTES.md`, PR descriptions, and commit
history from Week 3 integration work. Ordered by when each was found/fixed.

## 1. Role casing: `"User"/"Moderator"` (contract) vs `'user'/'moderator'` (DB, JWT)

`docs/API_CONTRACT.md` documents `POST /auth/login`'s response as
`"role": "User | Moderator"`, but `backend/auth/schema.sql`'s enum and every issued JWT
used lowercase `'user'`/`'moderator'`. `backend/recipes/token_auth.py`'s role check
compared against the capitalized contract strings, so it could never match — every real
login 401'd on recipe write routes (create/update/delete/rate).

Fixed in [PR #29](https://github.com/xd-dbug/PRO305/pull/29) (closes #28, merged 2026-08-17): the check now
compares against the lowercase values actually in use. The contract doc's casing in the
example JSON is cosmetic and wasn't changed; the fix was on the backend comparison.

## 2. Two auth helpers, two different user-object shapes

`backend/recipes/app.py` imported `require_owner_or_moderator` from both the
recipes-local `token_auth.py` (user dict shaped `{user_id, role}`) and the shared
`backend/layer/shared/auth_middleware.py` (expects the JWT's `sub` claim) — the shared
import won at runtime, but callers were still feeding it the `token_auth`-shaped dict.
Real owners were being 403'd on their own recipes; only moderators could update/delete
anything.

Fixed in [PR #32](https://github.com/xd-dbug/PRO305/pull/32) (closes #8, merged 2026-08-17): migrated
`recipes/app.py` fully onto the shared, tested `auth_middleware` and deleted the
now-redundant `token_auth.py`. Same PR also fixed an unrelated but similarly severe
import-time bug — `s3utils.py` vs. the `import s3_utils` in `app.py` — which broke the
entire recipes Lambda at cold start, not just one route.

## 3. Frontend built ahead of an undeployed route

`frontend/src/api/client.js` and `MealPlan.jsx` already called
`GET /mealplan/status/{jobId}` in the shape `docs/API_CONTRACT.md` specifies, but the
backend route had never been added to `infra/template.yaml` or implemented — confirmed
live via a `403 "Missing Authentication Token"` (API Gateway's "route doesn't exist"
response) rather than the `401` a real route returns without auth.

Fixed in [PR #51](https://github.com/xd-dbug/PRO305/pull/51) (closes #35, merged 2026-08-22): added the
missing route to `generate.py` (the same Lambda `POST /mealplan/generate` already runs —
see the `infra/README.md` note on `app.py`/`generate.py` naming), guarded by
`require_owner_or_moderator`. Also deleted `mealPlanMock.js`, which nothing imported
anymore once the real route existed.

## 4. Schema documented and coded, never applied to live RDS

While verifying [PR #47](https://github.com/xd-dbug/PRO305/pull/47) (closes #1, merged 2026-08-18), the
`dietary_tag`/`user_dietary_tag` tables added by PR #9's migration turned out to have
never actually been run against the live RDS instance —
`GET/PUT /users/me/preferences` was 500ing in prod despite the contract, schema file, and
frontend all agreeing on the shape. The migration existed in the repo; it just hadn't
been applied outside local/test environments. Applied directly against live RDS as part
of PR #47's verification.

## 5. `POST /recipes/{id}/save`: left undocumented, then built for real

Called out directly in `docs/RECIPES_WEEK2_NOTES.md`: the save endpoint was a no-op stub
through Week 2 — not in `API_CONTRACT.md`, not one of the three Week 2 recipes tickets.
Resolved in Week 4 (#78): backed by the `saved_recipe` table, with a matching `DELETE`
route and a `GET /recipes/saved` list endpoint, and the contract doc updated to match.

## 6. `avgRating`: zero vs. null was never specified

`docs/API_CONTRACT.md` always showed `avgRating` as a bare number (e.g. `4.2`) with no
note on what an unrated recipe returns. The backend returned `0.0`, which the frontend
rendered as a real (if low) rating instead of "not yet rated" — a display bug, but rooted
in the contract never specifying the unrated case. Fixed directly during Week 4
hardening: the backend now returns `null` for an unrated recipe, and the frontend
branches on that to show "Not yet rated". Worth adding an explicit `null` note to
`API_CONTRACT.md`'s `avgRating` fields (see #65).

## Pattern across all six

Every one of these survived local dev and unit tests and only surfaced against the real
deployed stack or a real JWT — none were caught by mocked-auth or mocked-DB tests. The
recurring shape is either two components (frontend/backend, contract doc/backend,
migration file/live DB) agreeing on paper but not at runtime, or a value convention
(role casing, zero vs. null) that the contract doc never pinned down precisely enough to
catch a mismatch by inspection alone.