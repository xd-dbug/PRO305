"""Route-level tests for POST /auth/register and POST /auth/login.

Follows the same load-by-path pattern as test_preferences_routes.py (app.py's
`from auth_service import ...` only resolves once the function's own
directory is on sys.path).
"""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

AUTH_DIR = Path(__file__).parent.parent
MODULE_PATH = AUTH_DIR / "app.py"

if str(AUTH_DIR) not in sys.path:
    sys.path.insert(0, str(AUTH_DIR))


def _load_app_module():
    spec = importlib.util.spec_from_file_location("auth_app_register_login", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["auth_app_register_login"] = module
    spec.loader.exec_module(module)
    return module


auth_app = _load_app_module()


class FakeContext:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "test-request-id"


def make_event(method, path, body=None):
    return {
        "httpMethod": method,
        "path": path,
        "resource": path,
        "headers": {"Content-Type": "application/json"},
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


def _mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


@patch("auth_app_register_login.hash_password", return_value="hashed-pw")
@patch("auth_app_register_login.get_connection")
def test_register_creates_user_and_returns_201(mock_get_conn, mock_hash):
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = None  # no existing user with this email
    cursor.lastrowid = 7
    mock_get_conn.return_value = conn

    body = {"email": "new@example.com", "password": "longenough", "displayName": "New User"}
    result = auth_app.lambda_handler(make_event("POST", "/auth/register", body), FakeContext())

    assert result["statusCode"] == 201
    payload = json.loads(result["body"])
    assert payload == {"userId": "7", "email": "new@example.com", "displayName": "New User"}
    conn.commit.assert_called_once()


@patch("auth_app_register_login.get_connection")
def test_register_rejects_duplicate_email(mock_get_conn):
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = {"id": 1}  # existing user
    mock_get_conn.return_value = conn

    body = {"email": "taken@example.com", "password": "longenough", "displayName": "Someone"}
    result = auth_app.lambda_handler(make_event("POST", "/auth/register", body), FakeContext())

    assert result["statusCode"] == 400


def test_register_rejects_missing_fields():
    body = {"email": "new@example.com", "password": "longenough"}  # no displayName
    result = auth_app.lambda_handler(make_event("POST", "/auth/register", body), FakeContext())
    assert result["statusCode"] == 400


def test_register_rejects_short_password():
    body = {"email": "new@example.com", "password": "short", "displayName": "New User"}
    result = auth_app.lambda_handler(make_event("POST", "/auth/register", body), FakeContext())
    assert result["statusCode"] == 400


@patch("auth_app_register_login.verify_password", return_value=True)
@patch("auth_app_register_login.get_connection")
def test_login_returns_user_id_and_role(mock_get_conn, mock_verify, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = {
        "id": 42,
        "email": "mod@example.com",
        "password_hash": "hashed",
        "role": "moderator",
    }
    mock_get_conn.return_value = conn

    body = {"email": "mod@example.com", "password": "whatever"}
    result = auth_app.lambda_handler(make_event("POST", "/auth/login", body), FakeContext())

    assert result["statusCode"] == 200
    payload = json.loads(result["body"])
    assert payload["userId"] == "42"
    assert payload["role"] == "moderator"
    assert "token" in payload
