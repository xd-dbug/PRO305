# API Contract — Week 1 Skeleton

Base URL: SAM Output `ApiUrl` (e.g. `https://<api-id>.execute-api.<region>.amazonaws.com/dev/`).
Locally: `sam local start-api` serves the same routes at `http://127.0.0.1:3000/`.

**Status:** all routes below are implemented as skeletons. `recipes/*` return mock data —
no database is queried yet. `auth/login` performs a real DB lookup + JWT issuance, but no
route enforces the resulting token yet.

## GET /health
Smoke-test route, no auth.

Response `200`:
```json
{ "status": "ok" }
```

## POST /auth/login
Request:
```json
{ "email": "alice@example.com", "password": "alice-test-password" }
```

Response `200`:
```json
{ "token": "<jwt>" }
```

Response `400` — missing email/password:
```json
{ "statusCode": 400, "message": "email and password are required" }
```

Response `401` — bad credentials:
```json
{ "statusCode": 401, "message": "invalid email or password" }
```

JWT payload shape: `{ "sub": "<user id>", "email": "...", "role": "user"|"moderator", "iat": ..., "exp": ... }`

## GET /recipes
Response `200` (mock data, always returns one placeholder recipe until DB logic lands):
```json
{
  "recipes": [
    {
      "id": 1,
      "title": "Placeholder Recipe",
      "description": "Stub data — no DB wired up yet",
      "ingredients": ["stub ingredient"],
      "steps": ["stub step"],
      "author_id": 1,
      "rating_avg": 0
    }
  ]
}
```

## GET /recipes/{recipe_id}
Response `200`: same shape as above, `id` set to the requested `{recipe_id}`.

## POST /recipes
Request: any subset of the recipe fields above (e.g. `{ "title": "Tacos" }`).
Response `201`: the submitted fields merged over the mock shape, `id` fixed at `999`
until DB logic lands.

## PUT /recipes/{recipe_id}
Request: same as POST. Response `200`: submitted fields merged over the mock shape,
`id` set to `{recipe_id}`.

## DELETE /recipes/{recipe_id}
Response `200`:
```json
{ "deleted": true, "id": 7 }
```

## POST /recipes/{recipe_id}/rate
Request:
```json
{ "rating": 5 }
```
Response `200`:
```json
{ "recipe_id": 7, "rating": 5, "rating_avg": 0 }
```

## POST /recipes/{recipe_id}/save
Response `200`:
```json
{ "recipe_id": 7, "saved": true }
```

## Error shape (all routes)
Powertools' event resolver returns errors as:
```json
{ "statusCode": <int>, "message": "<string>" }
```
