# API Contract

Frontend builds against this with mocked responses until backend endpoints are live. **Any change to this doc needs sign-off from the relevant backend owner (Auth: Person B, Recipes: Person A, Meal Plan: you) before frontend re-mocks around it — this is the one doc that, if it drifts silently, breaks integration week.**

Base URL: `https://<api-gateway-id>.execute-api.<region>.amazonaws.com/prod`

All authenticated routes require `Authorization: Bearer <jwt>`.

---

## Auth (Person B)

### POST /auth/register
```json
// Request
{ "email": "string", "password": "string", "displayName": "string" }
// Response 201
{ "userId": "string", "email": "string", "displayName": "string" }
```

### POST /auth/login
```json
// Request
{ "email": "string", "password": "string" }
// Response 200
{ "token": "jwt string", "userId": "string", "role": "User | Moderator" }
```
Errors: `401` invalid credentials

### GET /users/me/preferences  *(auth required)*
```json
// Response 200
{ "dietaryTags": ["vegetarian", "gluten-free"] }
```
Returns `{ "dietaryTags": [] }` if the user has never set any tags.
Errors: `401` unauthenticated

### PUT /users/me/preferences  *(auth required)*
```json
// Request
{ "dietaryTags": ["vegetarian", "gluten-free"] }
// Response 200 — same shape as GET
```
Full replace, not a merge — send the complete desired tag set. Send
`{ "dietaryTags": [] }` to clear all tags. Tags are normalized server-side
(trimmed, lowercased, deduplicated) so the mealplan prompt-building consumer
(issue #1) can match on exact string equality; the response echoes the
normalized values, which may differ in case from what was submitted.
Errors: `400` if `dietaryTags` is missing, not an array of strings, or
contains blank strings · `401` unauthenticated

---

## Recipes (Person A)

### GET /recipes
Query params: `?page=1&limit=20&tag=vegetarian`
```json
// Response 200
{
  "recipes": [
    { "recipeId": "string", "title": "string", "photoUrl": "string|null", "avgRating": 4.2, "authorId": "string" }
  ],
  "page": 1,
  "totalPages": 5
}
```

### GET /recipes/{recipeId}
```json
// Response 200
{
  "recipeId": "string", "title": "string", "authorId": "string",
  "ingredients": [{ "name": "string", "amount": "string" }],
  "steps": ["string"],
  "photoUrl": "string|null",
  "avgRating": 4.2,
  "tags": ["vegetarian"]
}
```

### POST /recipes  *(auth required)*
```json
// Request — same body as GET /recipes/{id} minus recipeId/avgRating
// Response 201 — full recipe object
```

### PUT /recipes/{recipeId}  *(auth required, author or Moderator only)*
Same body as POST. Response 200.

### DELETE /recipes/{recipeId}  *(auth required, author or Moderator only)*
Response 204. Errors: `403` if not author/Moderator.

### POST /recipes/{recipeId}/ratings  *(auth required)*
```json
// Request
{ "score": 5 }
// Response 201
{ "recipeId": "string", "avgRating": 4.3 }
```

### POST /recipes/{recipeId}/photo  *(auth required, author only)*
Multipart upload → S3. Response 200: `{ "photoUrl": "string" }`

---

## Meal Plan (you)

### POST /mealplan/generate  *(auth required)*
Enqueues to SQS, returns immediately.
```json
// Request
{ "preferences": { "days": 7, "mealsPerDay": 3 } }
// Response 202
{ "jobId": "string", "status": "pending" }
```

### GET /mealplan/status/{jobId}  *(auth required)*
Frontend polls this.
```json
// Response 200
{ "jobId": "string", "status": "pending | complete | failed", "mealPlan": null }
// when complete:
{ "jobId": "string", "status": "complete", "mealPlan": {
    "days": [ { "day": 1, "meals": [ { "recipeId": "string|null", "name": "string", "notes": "string" } ] } ]
} }
```
Polling interval: frontend should poll every 3–5s, stop after `failed` or `complete`, cap at ~2 min before showing a timeout state.

---

## Error shape (all endpoints)
```json
{ "error": "string", "message": "string" }
```
Standard codes: `400` validation, `401` unauthenticated, `403` forbidden, `404` not found, `500` server error.
