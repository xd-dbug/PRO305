import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).parent.parent / "app.py"


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


def make_event(method, path, path_params=None, body=None):
    return {
        "httpMethod": method,
        "path": path,
        "resource": path,
        "headers": {"Content-Type": "application/json"},
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


recipes_app = _load_app_module()


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
        make_event("POST", "/recipes", body={"title": "Tacos"}), FakeContext()
    )
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["title"] == "Tacos"


def test_update_recipe_returns_requested_id():
    result = recipes_app.lambda_handler(
        make_event("PUT", "/recipes/7", body={"title": "Updated"}), FakeContext()
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == 7
    assert body["title"] == "Updated"


def test_delete_recipe_confirms_deletion():
    result = recipes_app.lambda_handler(make_event("DELETE", "/recipes/7"), FakeContext())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["deleted"] is True
    assert body["id"] == 7


def test_rate_recipe_echoes_rating():
    result = recipes_app.lambda_handler(
        make_event("POST", "/recipes/7/rate", body={"rating": 5}), FakeContext()
    )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["recipe_id"] == 7
    assert body["rating"] == 5


def test_save_recipe_confirms_saved():
    result = recipes_app.lambda_handler(make_event("POST", "/recipes/7/save"), FakeContext())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["saved"] is True
