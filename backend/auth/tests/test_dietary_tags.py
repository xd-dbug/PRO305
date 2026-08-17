"""DB-independent tests for the dietary-tags PUT body validation/normalization
in backend/auth/app.py (issue #9).

Loaded the same way test_auth_service.py loads auth_service.py — directly by
file path via importlib, rather than `import app`, so this doesn't require
`shared` (the Lambda layer) or `auth_service` to be resolvable on sys.path
just to exercise one pure helper. `_normalize_dietary_tags` doesn't touch the
DB, so it's safe to unit test directly; the routes themselves (get/update
preferences) are DB-dependent and are smoke-tested manually post-deploy per
the repo's testing convention (see backend/auth/tests/test_auth_service.py's
docstring pattern and docs/PROJECT_CONTEXT.md).
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from aws_lambda_powertools.event_handler.exceptions import BadRequestError

AUTH_DIR = Path(__file__).parent.parent
MODULE_PATH = AUTH_DIR / "app.py"


def _load_normalize_fn():
    """Load just the module namespace for app.py, without invoking any route.

    app.py does a bare `from auth_service import ...`, which only resolves
    if backend/auth/ is on sys.path — true for the real Lambda (SAM's
    CodeUri: ../backend/auth/ puts this directory at the import root) but
    not automatically true under pytest, so it's added here the same way
    backend/conftest.py adds the shared layer. Importing the module is
    enough to grab the pure `_normalize_dietary_tags` function — no route is
    called, so no DB connection is ever attempted.
    """
    if str(AUTH_DIR) not in sys.path:
        sys.path.insert(0, str(AUTH_DIR))
    spec = importlib.util.spec_from_file_location("auth_app", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app_module = _load_normalize_fn()
normalize = app_module._normalize_dietary_tags


def test_normalize_lowercases_and_trims():
    assert normalize({"dietaryTags": [" Vegetarian ", "Gluten-Free"]}) == [
        "vegetarian",
        "gluten-free",
    ]


def test_normalize_dedupes_case_insensitively():
    assert normalize({"dietaryTags": ["vegan", "Vegan", "VEGAN"]}) == ["vegan"]


def test_normalize_allows_empty_list_to_clear_tags():
    assert normalize({"dietaryTags": []}) == []


def test_normalize_rejects_missing_field():
    with pytest.raises(BadRequestError):
        normalize({})


def test_normalize_rejects_non_list():
    with pytest.raises(BadRequestError):
        normalize({"dietaryTags": "vegetarian"})


def test_normalize_rejects_non_string_entries():
    with pytest.raises(BadRequestError):
        normalize({"dietaryTags": ["vegetarian", 5]})


def test_normalize_rejects_blank_entries():
    with pytest.raises(BadRequestError):
        normalize({"dietaryTags": ["vegetarian", "   "]})
