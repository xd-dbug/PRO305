import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parent.parent / "app.py"


def _load():
    spec = importlib.util.spec_from_file_location("mealplan_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mealplan_app = _load()


def _sqs_event(bodies):
    return {
        "Records": [
            {
                "messageId": f"test-message-{i}",
                "body": body,
            }
            for i, body in enumerate(bodies)
        ]
    }


def test_handles_empty_batch():
    result = mealplan_app.lambda_handler({"Records": []}, {})
    assert result == {"processed": 0}


def test_processes_each_record_in_batch():
    event = _sqs_event(['{"jobId": "abc123"}', '{"jobId": "def456"}'])
    result = mealplan_app.lambda_handler(event, {})
    assert result == {"processed": 2}


def test_missing_records_key_treated_as_empty():
    result = mealplan_app.lambda_handler({}, {})
    assert result == {"processed": 0}
