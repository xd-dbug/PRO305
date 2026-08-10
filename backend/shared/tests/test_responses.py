import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).parent.parent / "responses.py"


def _load():
    spec = importlib.util.spec_from_file_location("responses", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


responses = _load()


def test_success_default_status():
    result = responses.success({"ok": True})
    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == {"ok": True}


def test_error_default_status():
    result = responses.error("boom")
    assert result["statusCode"] == 500
    assert json.loads(result["body"]) == {"error": "boom"}


def test_error_custom_status():
    result = responses.error("not found", status_code=404)
    assert result["statusCode"] == 404