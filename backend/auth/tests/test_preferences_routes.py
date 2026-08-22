"""Route-level auth-enforcement tests for GET/PUT /users/me/preferences — issue #40.

backend/auth/tests/test_dietary_tags.py deliberately only unit-tests the
DB-independent `_normalize_dietary_tags` helper and says the routes
themselves are "smoke-tested manually post-deploy" — which means there was
no automated proof that get_preferences/update_preferences actually call
require_auth at all. Both routes call require_auth(app) as their first line,
before any DB access, so the missing-token case can be exercised the same
way backend/recipes/tests/test_recipes_routes.py does it: load app.py by
file path, invoke lambda_handler with no Authorization header, and check for
a 401 — no fake DB needed since the request never reaches get_connection().
"""
import importlib.util
import sys
from pathlib import Path

AUTH_DIR = Path(__file__).parent.parent
MODULE_PATH = AUTH_DIR / "app.py"

# app.py does `from auth_service import ...` — a local, non-package import
# that only resolves at deploy time (SAM puts the function's own directory
# on sys.path). Mirror that here, same pattern as
# backend/recipes/tests/test_recipes_routes.py's RECIPES_DIR insertion.
if str(AUTH_DIR) not in sys.path:
    sys.path.insert(0, str(AUTH_DIR))


def _load_app_module():
    spec = importlib.util.spec_from_file_location("auth_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auth_app = _load_app_module()


class FakeContext:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "test-request-id"


def make_event(method, path, body=None, headers=None):
    import json

    return {
        "httpMethod": method,
        "path": path,
        "resource": path,
        "headers": {"Content-Type": "application/json", **(headers or {})},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
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


def test_get_preferences_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    result = auth_app.lambda_handler(make_event("GET", "/users/me/preferences"), FakeContext())
    assert result["statusCode"] == 401


def test_update_preferences_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    result = auth_app.lambda_handler(
        make_event("PUT", "/users/me/preferences", body={"dietaryTags": ["vegetarian"]}),
        FakeContext(),
    )
    assert result["statusCode"] == 401
