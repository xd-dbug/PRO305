import importlib.util
import json
from pathlib import Path

import jwt
import pytest

MODULE_PATH = Path(__file__).parent.parent / "app.py"

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

# The mock recipe's author_id (see app.py) — used to build "owner" vs "non-owner" tokens.
OWNER_SUB = "1"


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)


def test_list_recipes_returns_mock_list():
    result = recipes_app.lambda_handler(make_event("GET", "/recipes"), FakeContext())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert isinstance(body["recipes"], list)
    assert len(body["recipes"]) >= 1


def test_get_recipe_returns_requested_id():
    result = recipes_app.lambda_handler(make_event("GET", "/recipes/42"), FakeContext())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == 42


def test_create_recipe_returns_201_with_submitted_fields():
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes", body={"title": "Tacos"}, headers=auth_headers()),
        FakeContext(),
    )
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["title"] == "Tacos"


def test_create_recipe_rejects_missing_token():
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes", body={"title": "Tacos"}), FakeContext()
    )
    assert result["statusCode"] == 401


def test_create_recipe_rejects_invalid_token():
    result = recipes_app.lambda_handler(
        make_event(
            "POST",
            "/recipes",
            body={"title": "Tacos"},
            headers={"Authorization": "Bearer not-a-real-token"},
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 401


def test_update_recipe_returns_requested_id_for_owner():
    result = recipes_app.lambda_handler(
        make_event(
            "PUT",
            "/recipes/7",
            body={"title": "Updated"},
            headers=auth_headers(role="user", sub=OWNER_SUB),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == 7
    assert body["title"] == "Updated"


def test_update_recipe_allows_moderator_regardless_of_ownership():
    result = recipes_app.lambda_handler(
        make_event(
            "PUT",
            "/recipes/7",
            body={"title": "Updated"},
            headers=auth_headers(role="moderator", sub="999"),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 200


def test_update_recipe_rejects_missing_token():
    result = recipes_app.lambda_handler(
        make_event("PUT", "/recipes/7", body={"title": "Updated"}), FakeContext()
    )
    assert result["statusCode"] == 401


def test_update_recipe_rejects_non_owner_non_moderator():
    result = recipes_app.lambda_handler(
        make_event(
            "PUT",
            "/recipes/7",
            body={"title": "Updated"},
            headers=auth_headers(role="user", sub="999"),
        ),
        FakeContext(),
    )
    assert result["statusCode"] == 403


def test_delete_recipe_confirms_deletion_for_owner():
    result = recipes_app.lambda_handler(
        make_event("DELETE", "/recipes/7", headers=auth_headers(role="user", sub=OWNER_SUB)),
        FakeContext(),
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["deleted"] is True
    assert body["id"] == 7


def test_delete_recipe_rejects_non_owner_non_moderator():
    result = recipes_app.lambda_handler(
        make_event("DELETE", "/recipes/7", headers=auth_headers(role="user", sub="999")),
        FakeContext(),
    )
    assert result["statusCode"] == 403


def test_delete_recipe_rejects_missing_token():
    result = recipes_app.lambda_handler(make_event("DELETE", "/recipes/7"), FakeContext())
    assert result["statusCode"] == 401


def test_rate_recipe_echoes_rating():
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes/7/rate", body={"rating": 5}, headers=auth_headers()),
        FakeContext(),
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["recipe_id"] == 7
    assert body["rating"] == 5


def test_rate_recipe_rejects_missing_token():
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes/7/rate", body={"rating": 5}), FakeContext()
    )
    assert result["statusCode"] == 401


def test_save_recipe_confirms_saved():
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes/7/save", headers=auth_headers()), FakeContext()
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["saved"] is True


def test_save_recipe_rejects_missing_token():
    result = recipes_app.lambda_handler(make_event("POST", "/recipes/7/save"), FakeContext())
    assert result["statusCode"] == 401
