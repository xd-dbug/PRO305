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