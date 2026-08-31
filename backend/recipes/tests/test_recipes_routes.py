"""Route tests for backend/recipes/app.py.

Focused on auth/ownership wiring (issue #8): app.py used to import a local
`get_current_user`/`require_owner_or_moderator` from token_auth.py *and* the
shared, tested shared.auth_middleware versions in the same statement block,
with the second import silently winning. That meant update_recipe/delete_recipe
called require_owner_or_moderator with a user dict shaped {"user_id", "role"}
(token_auth.py's shape) against an implementation that reads user["sub"]
(shared.auth_middleware's shape) — so `sub` was always missing and real
recipe owners got incorrectly 403'd on their own recipes.

app.py's routes are all DB-backed (real MySQL/RDS, VPC-bound, not reachable
from sam local per the repo's testing convention) so these tests monkeypatch
get_connection with the tiny in-memory fake in fake_db.py rather than hitting
a real database — see fake_db.py's docstring for the scope/limits of that
fake. This is not a substitute for the manual post-deploy smoke test of the
actual DB-dependent behavior; it exists to make the auth-enforcement logic
itself unit-testable and to regression-test the shadowed-import bug above.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import jwt
import pytest

RECIPES_DIR = Path(__file__).parent.parent
MODULE_PATH = RECIPES_DIR / "app.py"

# app.py does local (non-package) imports of s3_utils/multipart_utils — those
# only resolve at deploy time because Lambda puts the function root on
# sys.path. Mirror that here for the spec_from_file_location load below.
if str(RECIPES_DIR) not in sys.path:
    sys.path.insert(0, str(RECIPES_DIR))

# s3_utils.py builds a real boto3 S3 client at *import* time (module-level),
# not lazily per-call. None of these tests exercise the photo-upload S3 calls
# themselves, but importing app.py (which imports s3_utils) still triggers
# boto3's credential resolution, which can hard-fail in an environment with
# no AWS credentials/config at all. Dummy static credentials are enough to
# satisfy client construction without making any real AWS calls or reading
# a real profile/SSO config — this keeps the test run independent of
# whatever credentials happen to be in the invoking shell.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

from fake_db import FakeConnection, FakeDB  # noqa: E402  (tests/ dir is on sys.path via pytest's own rootdir insertion)

JWT_SECRET = "test-secret"


def _load_app_module():
    spec = importlib.util.spec_from_file_location("recipes_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeContext:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "test-request-id"


def make_event(method, path, path_params=None, body=None, headers=None):
    return {
        "httpMethod": method,
        "path": path,
        "resource": path,
        "headers": {"Content-Type": "application/json", **(headers or {})},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": path_params,
        "stageVariables": None,
        "requestContext": {
            "httpMethod": method,
            "path": path,
            "resourcePath": path,
            "stage": "test",
            "requestId": "test-request-id",
            "identity": {},
        },
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


def make_token(role="user", sub="1", secret=JWT_SECRET):
    return jwt.encode({"sub": sub, "email": "alice@example.com", "role": role}, secret, algorithm="HS256")


def auth_headers(role="user", sub="1", secret=JWT_SECRET):
    return {"Authorization": f"Bearer {make_token(role=role, sub=sub, secret=secret)}"}


recipes_app = _load_app_module()

# The seeded recipe's author — used to build "owner" vs "non-owner" tokens.
OWNER_SUB = "1"
OTHER_SUB = "999"
RECIPE_ID = 7

VALID_BODY = {
    "title": "Updated Tacos",
    "ingredients": [{"name": "tortilla", "amount": "2"}],
    "steps": ["Warm the tortilla", "Add filling"],
    "tags": [],
}


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    db.seed_recipe(RECIPE_ID, author_id=OWNER_SUB)
    monkeypatch.setattr(recipes_app, "get_connection", lambda: FakeConnection(db))
    return db


# ---------------------------------------------------------------------------
# update_recipe (PUT /recipes/{id}) — auth required, author or Moderator only
# ---------------------------------------------------------------------------

def test_update_recipe_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event("PUT", f"/recipes/{RECIPE_ID}", path_params={"recipe_id": str(RECIPE_ID)}, body=VALID_BODY),
        FakeContext(),
    )
    assert result["statusCode"] == 401


def test_update_recipe_rejects_non_owner_non_moderator(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "PUT",
            f"/recipes/{RECIPE_ID}",
            path_params={"recipe_id": str(RECIPE_ID)},
            body=VALID_BODY,
            headers=auth_headers(role="user", sub=OTHER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 403


def test_update_recipe_allows_owner(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "PUT",
            f"/recipes/{RECIPE_ID}",
            path_params={"recipe_id": str(RECIPE_ID)},
            body=VALID_BODY,
            headers=auth_headers(role="user", sub=OWNER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["title"] == VALID_BODY["title"]


def test_update_recipe_allows_moderator_regardless_of_ownership(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "PUT",
            f"/recipes/{RECIPE_ID}",
            path_params={"recipe_id": str(RECIPE_ID)},
            body=VALID_BODY,
            headers=auth_headers(role="moderator", sub=OTHER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 200


# ---------------------------------------------------------------------------
# delete_recipe (DELETE /recipes/{id}) — auth required, author or Moderator only
# ---------------------------------------------------------------------------

def test_delete_recipe_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event("DELETE", f"/recipes/{RECIPE_ID}", path_params={"recipe_id": str(RECIPE_ID)}),
        FakeContext(),
    )
    assert result["statusCode"] == 401


def test_delete_recipe_rejects_non_owner_non_moderator(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "DELETE",
            f"/recipes/{RECIPE_ID}",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers=auth_headers(role="user", sub=OTHER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 403
    assert RECIPE_ID in fake_db.recipes  # rejected before the delete happened


def test_delete_recipe_allows_owner(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "DELETE",
            f"/recipes/{RECIPE_ID}",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers=auth_headers(role="user", sub=OWNER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 204
    assert RECIPE_ID not in fake_db.recipes


def test_delete_recipe_allows_moderator_regardless_of_ownership(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "DELETE",
            f"/recipes/{RECIPE_ID}",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers=auth_headers(role="moderator", sub=OTHER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 204
    assert RECIPE_ID not in fake_db.recipes


# ---------------------------------------------------------------------------
# create_recipe / rate_recipe — auth required, no ownership check, but must
# use the token's `sub` (not token_auth.py's `user_id`) as the actor id.
# ---------------------------------------------------------------------------

def test_create_recipe_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes", body=VALID_BODY), FakeContext()
    )
    assert result["statusCode"] == 401


def test_create_recipe_uses_token_sub_as_author(fake_db):
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes", body=VALID_BODY, headers=auth_headers(role="user", sub="42")),
        FakeContext(),
    )
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["authorId"] == "42"


def test_create_recipe_persists_servings_prep_cook_notes(fake_db):
    body = {
        **VALID_BODY,
        "servings": "4",
        "prepTime": "15 min",
        "cookTime": "30 min",
        "notes": "Double the garlic.",
    }
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes", body=body, headers=auth_headers(role="user", sub="42")),
        FakeContext(),
    )
    assert result["statusCode"] == 201
    created = json.loads(result["body"])
    assert created["servings"] == "4"
    assert created["prepTime"] == "15 min"
    assert created["cookTime"] == "30 min"
    assert created["notes"] == "Double the garlic."


def test_rate_recipe_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event("POST", f"/recipes/{RECIPE_ID}/ratings", body={"score": 5}),
        FakeContext(),
    )
    assert result["statusCode"] == 401


def test_rate_recipe_records_score_against_token_sub(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "POST",
            f"/recipes/{RECIPE_ID}/ratings",
            body={"score": 5},
            headers=auth_headers(role="user", sub=OWNER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 201
    assert fake_db.ratings[(RECIPE_ID, OWNER_SUB)] == 5

# ---------------------------------------------------------------------------
# upload_photo (POST /recipes/{id}/photo) and save_recipe (POST /recipes/{id}/save)
# — issue #40. Neither route had a missing-token test before this; both call
# require_auth(app) as their first line (before touching the DB), so a
# missing/invalid header should 401 without needing a seeded recipe.
# ---------------------------------------------------------------------------

def test_upload_photo_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "POST",
            f"/recipes/{RECIPE_ID}/photo",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers={"Content-Type": "multipart/form-data; boundary=x"},
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 401


def test_upload_photo_rejects_non_owner_non_moderator(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "POST",
            f"/recipes/{RECIPE_ID}/photo",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers={
                "Content-Type": "multipart/form-data; boundary=x",
                **auth_headers(role="user", sub=OTHER_SUB),
            },
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 403


def test_upload_photo_allows_moderator_regardless_of_ownership(fake_db):
    # Moderator clears the ownership check (the thing under test). No real
    # "file" field is given — per the module comment above, these tests
    # don't exercise the S3 calls — so it should 400 on the empty multipart
    # body, not 403 on ownership.
    event = make_event(
        "POST",
        f"/recipes/{RECIPE_ID}/photo",
        path_params={"recipe_id": str(RECIPE_ID)},
        headers={
            "Content-Type": "multipart/form-data; boundary=x",
            **auth_headers(role="moderator", sub=OTHER_SUB),
        },
    )
    event["body"] = "--x--\r\n"
    result = recipes_app.lambda_handler(event, FakeContext())
    assert result["statusCode"] == 400


def test_upload_photo_400s_on_missing_body_instead_of_crashing(fake_db):
    # A multipart Content-Type with no body at all (event.body is None) used
    # to raise an unhandled AttributeError instead of a clean 400.
    result = recipes_app.lambda_handler(
        make_event(
            "POST",
            f"/recipes/{RECIPE_ID}/photo",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers={
                "Content-Type": "multipart/form-data; boundary=x",
                **auth_headers(role="user", sub=OWNER_SUB),
            },
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 400


def test_save_recipe_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event("POST", f"/recipes/{RECIPE_ID}/save", path_params={"recipe_id": str(RECIPE_ID)}),
        FakeContext(),
    )
    assert result["statusCode"] == 401


def test_save_recipe_persists_and_is_idempotent(fake_db):
    event = make_event(
        "POST",
        f"/recipes/{RECIPE_ID}/save",
        path_params={"recipe_id": str(RECIPE_ID)},
        headers=auth_headers(role="user", sub=OWNER_SUB),
    )
    first = recipes_app.lambda_handler(event, FakeContext())
    second = recipes_app.lambda_handler(event, FakeContext())

    assert first["statusCode"] == 200
    assert second["statusCode"] == 200
    assert json.loads(first["body"]) == {"recipeId": str(RECIPE_ID), "saved": True}
    assert fake_db.saved.count((OWNER_SUB, RECIPE_ID)) == 1


def test_save_recipe_404s_for_unknown_recipe(fake_db):
    result = recipes_app.lambda_handler(
        make_event(
            "POST",
            "/recipes/9999/save",
            path_params={"recipe_id": "9999"},
            headers=auth_headers(role="user", sub=OWNER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 404


def test_unsave_recipe_removes_it(fake_db):
    fake_db.saved.append((OWNER_SUB, RECIPE_ID))
    result = recipes_app.lambda_handler(
        make_event(
            "DELETE",
            f"/recipes/{RECIPE_ID}/save",
            path_params={"recipe_id": str(RECIPE_ID)},
            headers=auth_headers(role="user", sub=OWNER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 204
    assert (OWNER_SUB, RECIPE_ID) not in fake_db.saved


def test_list_saved_recipes_rejects_missing_token(fake_db):
    result = recipes_app.lambda_handler(
        make_event("GET", "/recipes/saved"), FakeContext()
    )
    assert result["statusCode"] == 401


def test_list_saved_recipes_returns_only_current_users_saves(fake_db):
    fake_db.seed_recipe(RECIPE_ID + 1, author_id=OTHER_SUB, title="Someone else's")
    fake_db.saved.append((OWNER_SUB, RECIPE_ID))
    fake_db.saved.append((OTHER_SUB, RECIPE_ID + 1))

    result = recipes_app.lambda_handler(
        make_event("GET", "/recipes/saved", headers=auth_headers(role="user", sub=OWNER_SUB)),
        FakeContext(),
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert [r["recipeId"] for r in body["recipes"]] == [str(RECIPE_ID)]