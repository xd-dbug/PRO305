import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

MEALPLAN_DIR = Path(__file__).parent.parent
MODULE_PATH = MEALPLAN_DIR / "app.py"


def _load():
    if str(MEALPLAN_DIR) not in sys.path:
        sys.path.insert(0, str(MEALPLAN_DIR))
    spec = importlib.util.spec_from_file_location("mealplan_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["mealplan_app"] = module
    spec.loader.exec_module(module)
    return module


mealplan_app = _load()


class FakeContext:
    function_name = "test"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    aws_request_id = "test-request-id"


class FakeTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


def _sqs_event(bodies):
    return {
        "Records": [
            {"messageId": f"test-message-{i}", "body": body}
            for i, body in enumerate(bodies)
        ]
    }


def _mock_conn(fetchone_return):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_return
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


def _update_calls(cursor, keyword):
    return [c for c in cursor.execute.call_args_list if keyword in c.args[0]]


def test_handles_empty_batch():
    result = mealplan_app.lambda_handler({"Records": []}, FakeContext())
    assert result == {"processed": 0}


def test_missing_records_key_treated_as_empty():
    result = mealplan_app.lambda_handler({}, FakeContext())
    assert result == {"processed": 0}


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("mealplan_app.anthropic")
@patch("mealplan_app.get_saved_recipes")
@patch("mealplan_app.get_dietary_tags")
@patch("mealplan_app.get_connection")
def test_success_marks_complete_with_generated_plan(
    mock_get_conn, mock_get_dietary_tags, mock_get_saved_recipes, mock_anthropic
):
    conn, cursor = _mock_conn(
        {"user_id": 7, "request_preferences": json.dumps({"days": 2, "mealsPerDay": 2})}
    )
    mock_get_conn.return_value = conn
    mock_get_dietary_tags.return_value = ["vegetarian"]
    mock_get_saved_recipes.return_value = [{"title": "Oat Bowl", "rating_avg": "4.50"}]

    plan = {"days": [{"day": 1, "meals": [{"recipeId": None, "name": "Oats", "notes": ""}]}]}
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[FakeTextBlock(json.dumps(plan))])
    mock_anthropic.Anthropic.return_value = client

    event = _sqs_event([json.dumps({"jobId": "job-1"})])
    result = mealplan_app.lambda_handler(event, FakeContext())

    assert result == {"processed": 1}

    mock_get_dietary_tags.assert_called_once_with(conn, 7)
    mock_get_saved_recipes.assert_called_once_with(conn, 7)

    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "vegetarian" in prompt
    assert "Oat Bowl" in prompt

    complete_calls = _update_calls(cursor, "status = 'complete'")
    assert len(complete_calls) == 1
    _, params = complete_calls[0].args
    assert json.loads(params[0]) == plan
    assert params[1] == "job-1"

    conn.commit.assert_called_once()
    conn.close.assert_called_once()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("mealplan_app.anthropic")
@patch("mealplan_app.get_saved_recipes")
@patch("mealplan_app.get_dietary_tags")
@patch("mealplan_app.get_connection")
def test_success_emits_generation_duration_metric(
        mock_get_conn, mock_get_dietary_tags, mock_get_saved_recipes, mock_anthropic, capsys
):
    conn, cursor = _mock_conn(
        {"user_id": 7, "request_preferences": json.dumps({"days": 1, "mealsPerDay": 1})}
    )
    mock_get_conn.return_value = conn
    mock_get_dietary_tags.return_value = []
    mock_get_saved_recipes.return_value = []

    plan = {"days": [{"day": 1, "meals": [{"recipeId": None, "name": "Oats", "notes": ""}]}]}
    client = MagicMock()
    client.messages.create.return_value = MagicMock(content=[FakeTextBlock(json.dumps(plan))])
    mock_anthropic.Anthropic.return_value = client

    event = _sqs_event([json.dumps({"jobId": "job-metric"})])
    mealplan_app.lambda_handler(event, FakeContext())

    emf = json.loads(capsys.readouterr().out)
    metric_defs = emf["_aws"]["CloudWatchMetrics"][0]
    assert metric_defs["Namespace"] == "RecipeSharing/Mealplan"
    assert {"Name": "GenerationDurationMs", "Unit": "Milliseconds"} in metric_defs["Metrics"]
    assert emf["GenerationDurationMs"][0] >= 0


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("mealplan_app.anthropic")
@patch("mealplan_app.get_connection")
def test_missing_job_row_marks_failed_and_reraises(mock_get_conn, mock_anthropic):
    conn, cursor = _mock_conn(None)
    mock_get_conn.return_value = conn

    event = _sqs_event([json.dumps({"jobId": "missing-job"})])
    with pytest.raises(ValueError):
        mealplan_app.lambda_handler(event, FakeContext())

    failed_calls = _update_calls(cursor, "status = 'failed'")
    assert len(failed_calls) == 1
    _, params = failed_calls[0].args
    assert "missing-job" in params[0]
    assert params[1] == "missing-job"

    mock_anthropic.Anthropic.assert_not_called()
    conn.commit.assert_called_once()
    conn.close.assert_called_once()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("mealplan_app.anthropic")
@patch("mealplan_app.get_saved_recipes")
@patch("mealplan_app.get_dietary_tags")
@patch("mealplan_app.get_connection")
def test_claude_failure_marks_failed_and_reraises(
    mock_get_conn, mock_get_dietary_tags, mock_get_saved_recipes, mock_anthropic
):
    conn, cursor = _mock_conn(
        {"user_id": 7, "request_preferences": json.dumps({"days": 1, "mealsPerDay": 1})}
    )
    mock_get_conn.return_value = conn
    mock_get_dietary_tags.return_value = []
    mock_get_saved_recipes.return_value = []

    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("claude is down")
    mock_anthropic.Anthropic.return_value = client

    event = _sqs_event([json.dumps({"jobId": "job-2"})])
    with pytest.raises(RuntimeError):
        mealplan_app.lambda_handler(event, FakeContext())

    failed_calls = _update_calls(cursor, "status = 'failed'")
    assert len(failed_calls) == 1
    _, params = failed_calls[0].args
    assert params[0] == "claude is down"
    assert params[1] == "job-2"

    conn.commit.assert_called_once()
    conn.close.assert_called_once()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("mealplan_app.anthropic")
@patch("mealplan_app.get_saved_recipes")
@patch("mealplan_app.get_dietary_tags")
@patch("mealplan_app.get_connection")
def test_malformed_claude_json_marks_failed_and_reraises(
    mock_get_conn, mock_get_dietary_tags, mock_get_saved_recipes, mock_anthropic
):
    conn, cursor = _mock_conn(
        {"user_id": 7, "request_preferences": json.dumps({"days": 1, "mealsPerDay": 1})}
    )
    mock_get_conn.return_value = conn
    mock_get_dietary_tags.return_value = []
    mock_get_saved_recipes.return_value = []

    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[FakeTextBlock("not valid json")]
    )
    mock_anthropic.Anthropic.return_value = client

    event = _sqs_event([json.dumps({"jobId": "job-3"})])
    with pytest.raises(json.JSONDecodeError):
        mealplan_app.lambda_handler(event, FakeContext())

    failed_calls = _update_calls(cursor, "status = 'failed'")
    assert len(failed_calls) == 1
    _, params = failed_calls[0].args
    assert params[1] == "job-3"