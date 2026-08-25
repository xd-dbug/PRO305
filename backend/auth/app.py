import json
import os

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig, Response
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, UnauthorizedError

from auth_service import hash_password, issue_token, verify_password
from shared.auth_middleware import require_auth
from shared.db import get_connection

app = APIGatewayRestResolver(cors=CORSConfig(allow_origin="http://localhost:5173"))

MIN_PASSWORD_LENGTH = 8


# ---------------------------------------------------------------------------
# Dietary preference tags helpers (issue #9)
# ---------------------------------------------------------------------------

def _fetch_dietary_tags(cursor, user_id):
    cursor.execute(
        """
        SELECT dt.name FROM dietary_tag dt
        JOIN user_dietary_tag udt ON udt.dietary_tag_id = dt.id
        WHERE udt.user_id = %s
        ORDER BY dt.name
        """,
        (user_id,),
    )
    return [row["name"] for row in cursor.fetchall()]


def _normalize_dietary_tags(body):
    """Validate the PUT body and normalize tag names.

    Tags are lowercased/trimmed so the mealplan consumer (issue #1) doesn't
    have to deal with case variants of the same tag ("Vegetarian" vs
    "vegetarian"). An empty array is valid — it clears all tags.
    """
    tags = (body or {}).get("dietaryTags")
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise BadRequestError("dietaryTags must be an array of strings")

    normalized = []
    seen = set()
    for raw_tag in tags:
        cleaned = raw_tag.strip().lower()
        if not cleaned:
            raise BadRequestError("dietaryTags entries must be non-empty strings")
        if cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized


def _replace_dietary_tags(cursor, user_id, tags):
    """Full replace — simpler and less error-prone than diffing (mirrors
    recipes' _replace_ingredients_steps_tags in backend/recipes/app.py)."""
    cursor.execute("DELETE FROM user_dietary_tag WHERE user_id = %s", (user_id,))
    for tag_name in tags:
        cursor.execute("INSERT IGNORE INTO dietary_tag (name) VALUES (%s)", (tag_name,))
        cursor.execute("SELECT id FROM dietary_tag WHERE name = %s", (tag_name,))
        tag_id = cursor.fetchone()["id"]
        cursor.execute(
            "INSERT IGNORE INTO user_dietary_tag (user_id, dietary_tag_id) VALUES (%s, %s)",
            (user_id, tag_id),
        )


@app.post("/auth/register")
def register():
    body = app.current_event.json_body or {}
    email = body.get("email")
    password = body.get("password")
    display_name = body.get("displayName")
    if not email or not password or not display_name:
        raise BadRequestError("email, password, and displayName are required")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BadRequestError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone() is not None:
                raise BadRequestError("email is already registered")

            password_hash = hash_password(password)
            cursor.execute(
                "INSERT INTO users (email, password_hash, display_name) VALUES (%s, %s, %s)",
                (email, password_hash, display_name),
            )
            user_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return Response(
        status_code=201,
        content_type="application/json",
        body=json.dumps({"userId": str(user_id), "email": email, "displayName": display_name}),
    )


@app.post("/auth/login")
def login():
    body = app.current_event.json_body or {}
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        raise BadRequestError("email and password are required")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash, role FROM users WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
    finally:
        conn.close()

    if row is None or not verify_password(password, row["password_hash"]):
        raise UnauthorizedError("invalid email or password")

    token = issue_token(row["id"], row["email"], row["role"], secret=os.environ["JWT_SECRET"])
    return {"token": token, "userId": str(row["id"]), "role": row["role"]}


@app.get("/users/me/preferences")
def get_preferences():
    user = require_auth(app)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            tags = _fetch_dietary_tags(cursor, user["sub"])
    finally:
        conn.close()

    return {"dietaryTags": tags}


@app.put("/users/me/preferences")
def update_preferences():
    user = require_auth(app)
    tags = _normalize_dietary_tags(app.current_event.json_body)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            _replace_dietary_tags(cursor, user["sub"], tags)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {"dietaryTags": tags}


def lambda_handler(event, context):
    return app.resolve(event, context)
