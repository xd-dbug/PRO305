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
