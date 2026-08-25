import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

MEALPLAN_DIR = Path(__file__).parent.parent
MODULE_PATH = MEALPLAN_DIR / "generate.py"


def _load():
    # backend/conftest.py already puts the shared layer on sys.path, which is
    # the only sibling import generate.py needs (shared.db, shared.auth_middleware).
    spec = importlib.util.spec_from_file_location("mealplan_generate", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["mealplan_generate"] = module
    spec.loader.exec_module(module)
    return module


generate_module = _load()


class FakeContext:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "test-request-id"


def make_event(body):
    return {
        "httpMethod": "POST",
        "path": "/mealplan/generate",
        "resource": "/mealplan/generate",
        "headers": {"Content-Type": "application/json", "Authorization": "Bearer faketoken"},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "httpMethod": "POST",
            "path": "/mealplan/generate",
            "resourcePath": "/mealplan/generate",
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


def make_status_event(job_id):
    return {
        "httpMethod": "GET",
        "path": f"/mealplan/status/{job_id}",
        "resource": "/mealplan/status/{job_id}",
        "headers": {"Authorization": "Bearer faketoken"},
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": {"job_id": job_id},
        "stageVariables": None,
        "requestContext": {
            "httpMethod": "GET",
            "path": f"/mealplan/status/{job_id}",
            "resourcePath": "/mealplan/status/{job_id}",
            "stage": "test",
            "requestId": "test-request-id",
            "identity": {},
        },
        "body": None,
        "isBase64Encoded": False,
    }


@patch.dict("os.environ", {"MEALPLAN_QUEUE_URL": "https://sqs.fake/mealplan-queue"})
@patch("mealplan_generate.boto3")
@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_generate_inserts_pending_job_and_enqueues(mock_get_user, mock_get_conn, mock_boto3):
    mock_get_user.return_value = {"sub": "42", "email": "user@example.com", "role": "user"}
    conn, cursor = _mock_conn()
    mock_get_conn.return_value = conn
    sqs = MagicMock()
    mock_boto3.client.return_value = sqs

    event = make_event({"preferences": {"days": 3, "mealsPerDay": 2}})
    result = generate_module.lambda_handler(event, FakeContext())

    assert result["statusCode"] == 202
    body = json.loads(result["body"])
    assert body["status"] == "pending"
    assert "jobId" in body

    insert_sql, insert_params = cursor.execute.call_args[0]
    assert "INSERT INTO mealplan_job" in insert_sql
    assert insert_params[0] == body["jobId"]
    assert insert_params[1] == "42"
    assert json.loads(insert_params[2]) == {"days": 3, "mealsPerDay": 2}
    conn.commit.assert_called_once()
    conn.close.assert_called_once()

    sqs.send_message.assert_called_once()
    _, send_kwargs = sqs.send_message.call_args
    assert send_kwargs["QueueUrl"] == "https://sqs.fake/mealplan-queue"
    assert json.loads(send_kwargs["MessageBody"]) == {"jobId": body["jobId"]}


@patch("mealplan_generate.boto3")
@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_generate_rejects_missing_preferences(mock_get_user, mock_get_conn, mock_boto3):
    mock_get_user.return_value = {"sub": "42", "email": "user@example.com", "role": "user"}

    result = generate_module.lambda_handler(make_event({}), FakeContext())

    assert result["statusCode"] == 400
    mock_get_conn.assert_not_called()
    mock_boto3.client.assert_not_called()


@patch("mealplan_generate.boto3")
@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_generate_rejects_non_positive_days(mock_get_user, mock_get_conn, mock_boto3):
    mock_get_user.return_value = {"sub": "42", "email": "user@example.com", "role": "user"}

    body = {"preferences": {"days": 0, "mealsPerDay": 2}}
    result = generate_module.lambda_handler(make_event(body), FakeContext())

    assert result["statusCode"] == 400
    mock_get_conn.assert_not_called()


@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_status_returns_complete_job_with_plan(mock_get_user, mock_get_conn):
    mock_get_user.return_value = {"sub": "42", "email": "user@example.com", "role": "user"}
    plan = {"days": [{"day": 1, "meals": [{"recipeId": None, "name": "Oats", "notes": ""}]}]}
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = {
        "user_id": 42,
        "status": "complete",
        "generated_plan": json.dumps(plan),
    }
    mock_get_conn.return_value = conn

    result = generate_module.lambda_handler(make_status_event("job-1"), FakeContext())

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == {"jobId": "job-1", "status": "complete", "mealPlan": plan}
    conn.close.assert_called_once()


@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_status_returns_null_plan_while_pending(mock_get_user, mock_get_conn):
    mock_get_user.return_value = {"sub": "42", "email": "user@example.com", "role": "user"}
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = {"user_id": 42, "status": "pending", "generated_plan": None}
    mock_get_conn.return_value = conn

    result = generate_module.lambda_handler(make_status_event("job-2"), FakeContext())

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == {"jobId": "job-2", "status": "pending", "mealPlan": None}


@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_status_404s_for_unknown_job(mock_get_user, mock_get_conn):
    mock_get_user.return_value = {"sub": "42", "email": "user@example.com", "role": "user"}
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = None
    mock_get_conn.return_value = conn

    result = generate_module.lambda_handler(make_status_event("missing-job"), FakeContext())

    assert result["statusCode"] == 404


@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_status_403s_for_non_owner_non_moderator(mock_get_user, mock_get_conn):
    mock_get_user.return_value = {"sub": "99", "email": "other@example.com", "role": "user"}
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = {"user_id": 42, "status": "complete", "generated_plan": "{}"}
    mock_get_conn.return_value = conn

    result = generate_module.lambda_handler(make_status_event("job-3"), FakeContext())

    assert result["statusCode"] == 403


@patch("mealplan_generate.get_connection")
@patch("mealplan_generate.require_auth")
def test_status_allows_moderator_to_view_others_job(mock_get_user, mock_get_conn):
    mock_get_user.return_value = {"sub": "99", "email": "mod@example.com", "role": "moderator"}
    conn, cursor = _mock_conn()
    cursor.fetchone.return_value = {"user_id": 42, "status": "failed", "generated_plan": None}
    mock_get_conn.return_value = conn

    result = generate_module.lambda_handler(make_status_event("job-4"), FakeContext())

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body == {"jobId": "job-4", "status": "failed", "mealPlan": None}

# ---------------------------------------------------------------------------
# Real (unmocked) auth enforcement — issue #40.
#
# The tests below patch require_auth itself, which is correct for exercising
# generate()'s own logic but never proves the route is actually gated: a
# route that forgot to call require_auth at all would pass every test in
# this file unchanged. This test goes through the real require_auth/JWT
# path with no Authorization header and checks the route rejects with 401
# before it ever reaches get_connection/boto3, matching
# backend/recipes/tests/test_recipes_routes.py's *_rejects_missing_token
# pattern.
# ---------------------------------------------------------------------------

def test_generate_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    event = make_event({"preferences": {"days": 3, "mealsPerDay": 2}})
    del event["headers"]["Authorization"]

    response = generate_module.lambda_handler(event, FakeContext())

    assert response["statusCode"] == 401