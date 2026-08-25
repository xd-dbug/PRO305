"""
Recipes Lambda — Week 2.

Rewritten against the *actual* schema already in backend/recipes/schema.sql
(normalized: recipe_ingredient, recipe_step, tags/recipe_tag, singular
`rating` table, rating_avg stored on recipes) rather than the JSON-blob
design from an earlier draft of this file.

Uses shared.db.get_connection from the layer (backend/layer/shared/db.py).
That connection is NOT autocommit, so every write path here commits
explicitly and rolls back on failure.

S3 (s3_utils.py) and multipart parsing (multipart_utils.py) are local to
this component for now. Auth is the shared layer's
shared.auth_middleware (require_auth / require_owner_or_moderator) — see
that module's docstring. A local duplicate used to live in
token_auth.py; it's been retired in favor of the shared, tested
implementation (issue #8).
"""
import base64
import json

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
)

from shared.db import get_connection

import s3_utils
from multipart_utils import parse_multipart

from shared.auth_middleware import require_auth, require_owner_or_moderator

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="http://localhost:5173"))

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _photo_url(photo_key):
    return s3_utils.presign_read(photo_key) if photo_key else None


def _fetch_ingredients(cur, recipe_id):
    cur.execute(
        "SELECT name, amount FROM recipe_ingredient WHERE recipe_id = %s ORDER BY sort_order",
        (recipe_id,),
    )
    return [{"name": r["name"], "amount": r["amount"]} for r in cur.fetchall()]


def _fetch_steps(cur, recipe_id):
    cur.execute(
        "SELECT body FROM recipe_step WHERE recipe_id = %s ORDER BY step_number",
        (recipe_id,),
    )
    return [r["body"] for r in cur.fetchall()]


def _fetch_tags(cur, recipe_id):
    cur.execute(
        """
        SELECT t.name FROM tags t
        JOIN recipe_tag rt ON rt.tag_id = t.id
        WHERE rt.recipe_id = %s
        ORDER BY t.name
        """,
        (recipe_id,),
    )
    return [r["name"] for r in cur.fetchall()]


def _fetch_recipe_row_or_404(cur, recipe_id):
    cur.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    row = cur.fetchone()
    if not row:
        raise NotFoundError(f"Recipe {recipe_id} not found")
    return row


def _row_to_summary(row: dict) -> dict:
    return {
        "recipeId": str(row["id"]),
        "title": row["title"],
        "photoUrl": _photo_url(row.get("photo_url")),
        # rating_avg is NOT NULL DEFAULT 0 (never NULL) and ratings are 1-5,
        # so a real average can never be exactly 0 — falsy-check is how we
        # tell "never rated" apart from "has ratings" without a separate
        # rating_count column.
        "avgRating": float(row["rating_avg"]) if row.get("rating_avg") else None,
        "authorId": str(row["author_id"]),
    }


def _row_to_detail(cur, row: dict) -> dict:
    return {
        "recipeId": str(row["id"]),
        "title": row["title"],
        "authorId": str(row["author_id"]),
        "ingredients": _fetch_ingredients(cur, row["id"]),
        "steps": _fetch_steps(cur, row["id"]),
        "photoUrl": _photo_url(row.get("photo_url")),
        "avgRating": float(row["rating_avg"]) if row.get("rating_avg") else None,
        "tags": _fetch_tags(cur, row["id"]),
    }


# Match schema.sql's VARCHAR caps so oversized input gets a clean 400
# instead of hitting MySQL's data-too-long error as an unhandled 500.
MAX_TITLE_LENGTH = 255
MAX_INGREDIENT_NAME_LENGTH = 255
MAX_INGREDIENT_AMOUNT_LENGTH = 100
MAX_TAG_LENGTH = 50


def _validate_recipe_body(body: dict) -> dict:
    title = (body or {}).get("title")
    ingredients = (body or {}).get("ingredients")
    steps = (body or {}).get("steps")
    tags = (body or {}).get("tags", [])
    if not title or not isinstance(title, str):
        raise BadRequestError("title is required")
    if len(title) > MAX_TITLE_LENGTH:
        raise BadRequestError(f"title must be at most {MAX_TITLE_LENGTH} characters")
    if not isinstance(ingredients, list) or not ingredients:
        raise BadRequestError("ingredients must be a non-empty array")
    if not all(isinstance(i, dict) and i.get("name") and i.get("amount") for i in ingredients):
        raise BadRequestError("each ingredient needs name and amount")
    if not all(len(i["name"]) <= MAX_INGREDIENT_NAME_LENGTH for i in ingredients):
        raise BadRequestError(f"ingredient name must be at most {MAX_INGREDIENT_NAME_LENGTH} characters")
    if not all(len(i["amount"]) <= MAX_INGREDIENT_AMOUNT_LENGTH for i in ingredients):
        raise BadRequestError(f"ingredient amount must be at most {MAX_INGREDIENT_AMOUNT_LENGTH} characters")
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) for s in steps):
        raise BadRequestError("steps must be a non-empty array of strings")
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise BadRequestError("tags must be an array of strings")
    if not all(len(t) <= MAX_TAG_LENGTH for t in tags):
        raise BadRequestError(f"tag must be at most {MAX_TAG_LENGTH} characters")
    return {"title": title, "ingredients": ingredients, "steps": steps, "tags": tags}


def _replace_ingredients_steps_tags(cur, recipe_id, ingredients, steps, tags):
    """Full replace on PUT/POST — simpler and less error-prone than diffing."""
    cur.execute("DELETE FROM recipe_ingredient WHERE recipe_id = %s", (recipe_id,))
    cur.execute("DELETE FROM recipe_step WHERE recipe_id = %s", (recipe_id,))
    cur.execute("DELETE FROM recipe_tag WHERE recipe_id = %s", (recipe_id,))

    for i, ing in enumerate(ingredients):
        cur.execute(
            "INSERT INTO recipe_ingredient (recipe_id, name, amount, sort_order) VALUES (%s, %s, %s, %s)",
            (recipe_id, ing["name"], ing["amount"], i),
        )
    for i, step_body in enumerate(steps, start=1):
        cur.execute(
            "INSERT INTO recipe_step (recipe_id, step_number, body) VALUES (%s, %s, %s)",
            (recipe_id, i, step_body),
        )
    for tag_name in tags:
        cur.execute("INSERT IGNORE INTO tags (name) VALUES (%s)", (tag_name,))
        cur.execute("SELECT id FROM tags WHERE name = %s", (tag_name,))
        tag_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT IGNORE INTO recipe_tag (recipe_id, tag_id) VALUES (%s, %s)",
            (recipe_id, tag_id),
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@app.get("/recipes")
def list_recipes():
    q = app.current_event.query_string_parameters or {}
    try:
        page = max(int(q.get("page", 1)), 1)
        limit = min(max(int(q.get("limit", DEFAULT_PAGE_LIMIT)), 1), MAX_PAGE_LIMIT)
    except ValueError:
        raise BadRequestError("page and limit must be integers")
    tag = q.get("tag")
    offset = (page - 1) * limit

    conn = get_connection()
    with conn.cursor() as cur:
        if tag:
            where_sql = "WHERE r.id IN (SELECT rt.recipe_id FROM recipe_tag rt JOIN tags t ON t.id = rt.tag_id WHERE t.name = %s)"
            params = (tag,)
        else:
            where_sql = ""
            params = ()

        cur.execute(f"SELECT COUNT(*) AS total FROM recipes r {where_sql}", params)
        total = cur.fetchone()["total"]
        total_pages = max((total + limit - 1) // limit, 1)

        # ORDER BY needs a tiebreaker: created_at is a plain TIMESTAMP (1s
        # resolution, no fractional seconds), so any recipes inserted in the
        # same second — trivially true for bulk-seeded/test data, and not
        # impossible for real concurrent users — have no defined relative
        # order without one. Without `r.id DESC` here, MySQL doesn't
        # guarantee stable tie ordering between the COUNT query's plan and
        # the SELECT's, which can surface as the same recipe appearing on
        # two adjacent pages or disappearing between them (issue #39).
        cur.execute(
            f"""
            SELECT r.* FROM recipes r
            {where_sql}
            ORDER BY r.created_at DESC, r.id DESC
            LIMIT %s OFFSET %s
            """,
            (*params, limit, offset),
        )
        rows = cur.fetchall()

    return {
        "recipes": [_row_to_summary(r) for r in rows],
        "page": page,
        "totalPages": total_pages,
    }


@app.get("/recipes/<recipe_id>")
def get_recipe(recipe_id: str):
    conn = get_connection()
    with conn.cursor() as cur:
        row = _fetch_recipe_row_or_404(cur, recipe_id)
        detail = _row_to_detail(cur, row)
    return detail


@app.post("/recipes")
def create_recipe():
    user = require_auth(app)
    body = _validate_recipe_body(app.current_event.json_body)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO recipes (title, author_id) VALUES (%s, %s)",
                (body["title"], user["sub"]),
            )
            new_id = cur.lastrowid
            _replace_ingredients_steps_tags(cur, new_id, body["ingredients"], body["steps"], body["tags"])
            row = _fetch_recipe_row_or_404(cur, new_id)
            detail = _row_to_detail(cur, row)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return Response(status_code=201, content_type="application/json", body=json.dumps(detail))


@app.put("/recipes/<recipe_id>")
def update_recipe(recipe_id: str):
    user = require_auth(app)
    body = _validate_recipe_body(app.current_event.json_body)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            existing = _fetch_recipe_row_or_404(cur, recipe_id)
            require_owner_or_moderator(user, existing["author_id"])

            cur.execute("UPDATE recipes SET title = %s WHERE id = %s", (body["title"], recipe_id))
            _replace_ingredients_steps_tags(cur, recipe_id, body["ingredients"], body["steps"], body["tags"])
            row = _fetch_recipe_row_or_404(cur, recipe_id)
            detail = _row_to_detail(cur, row)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return detail


@app.delete("/recipes/<recipe_id>")
def delete_recipe(recipe_id: str):
    user = require_auth(app)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            existing = _fetch_recipe_row_or_404(cur, recipe_id)
            require_owner_or_moderator(user, existing["author_id"])
            # Child rows (recipe_ingredient, recipe_step, recipe_tag, rating,
            # saved_recipe) all cascade per schema.sql's ON DELETE CASCADE.
            cur.execute("DELETE FROM recipes WHERE id = %s", (recipe_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return Response(status_code=204, content_type="application/json", body="")


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------

@app.post("/recipes/<recipe_id>/ratings")
def rate_recipe(recipe_id: str):
    user = require_auth(app)
    body = app.current_event.json_body or {}
    score = body.get("score")
    if not isinstance(score, int) or not (1 <= score <= 5):
        raise BadRequestError("score must be an integer from 1 to 5")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _fetch_recipe_row_or_404(cur, recipe_id)

            # rating table has a UNIQUE(recipe_id, user_id) constraint —
            # re-rating updates the existing row instead of duplicating.
            cur.execute(
                """
                INSERT INTO rating (recipe_id, user_id, score)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE score = VALUES(score)
                """,
                (recipe_id, user["sub"], score),
            )

            cur.execute(
                "SELECT ROUND(AVG(score), 2) AS avg_score FROM rating WHERE recipe_id = %s",
                (recipe_id,),
            )
            avg_score = cur.fetchone()["avg_score"] or 0

            # rating_avg is stored on recipes (schema.sql), not computed
            # on read, so it has to be written back here.
            cur.execute(
                "UPDATE recipes SET rating_avg = %s WHERE id = %s",
                (avg_score, recipe_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return Response(
        status_code=201,
        content_type="application/json",
        body=json.dumps({"recipeId": str(recipe_id), "avgRating": float(avg_score)}),
    )


# ---------------------------------------------------------------------------
# Photo upload
# ---------------------------------------------------------------------------

@app.post("/recipes/<recipe_id>/photo")
def upload_photo(recipe_id: str):
    """Matches API_CONTRACT.md: multipart POST -> { "photoUrl": "string" }.
    Expects a single "file" field. Author only (not Moderator)."""
    user = require_auth(app)

    conn = get_connection()
    with conn.cursor() as cur:
        existing = _fetch_recipe_row_or_404(cur, recipe_id)
        if str(user["sub"]) != str(existing["author_id"]):
            raise ForbiddenError("Only the recipe author can upload its photo")

    event = app.current_event
    content_type_header = event.headers.get("Content-Type", "") or ""
    if "multipart/form-data" not in content_type_header:
        raise BadRequestError("Expected multipart/form-data with a 'file' field")

    raw_body = base64.b64decode(event.body) if event.is_base64_encoded else event.body.encode()
    fields = parse_multipart(content_type_header, raw_body)
    file_field = fields.get("file")
    if not file_field or not file_field["content"]:
        raise BadRequestError("Missing 'file' field in multipart body")

    content_type = file_field["content_type"]
    try:
        photo_key = s3_utils.new_photo_key(recipe_id, content_type)
    except ValueError as e:
        raise BadRequestError(str(e))

    s3_utils.upload_bytes(photo_key, file_field["content"], content_type)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE recipes SET photo_url = %s WHERE id = %s", (photo_key, recipe_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return {"photoUrl": s3_utils.presign_read(photo_key)}


# ---------------------------------------------------------------------------
# Untouched — not in API_CONTRACT.md, not part of this ticket's scope.
# ---------------------------------------------------------------------------
@app.post("/recipes/<recipe_id>/save")
def save_recipe(recipe_id: str):
    require_auth(app)
    return {"recipe_id": int(recipe_id), "saved": True}


def lambda_handler(event, context):
    return app.resolve(event, context)