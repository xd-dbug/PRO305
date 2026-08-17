import importlib.util
from pathlib import Path

import jwt
import pytest
from aws_lambda_powertools.event_handler.exceptions import ForbiddenError, UnauthorizedError

MODULE_PATH = Path(__file__).parent.parent / "shared" / "auth_middleware.py"


def _load():
    spec = importlib.util.spec_from_file_location("auth_middleware", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auth_middleware = _load()

SECRET = "test-secret"


class CaseInsensitiveHeaders(dict):
    """Minimal stand-in for powertools' real CaseInsensitiveDict headers."""

    def get(self, key, default=None):
        key_lower = key.lower()
        for k, v in self.items():
            if k.lower() == key_lower:
                return v
        return default


class FakeEvent:
    def __init__(self, headers):
        self.headers = CaseInsensitiveHeaders(headers or {})


class FakeApp:
    def __init__(self, headers=None):
        self.current_event = FakeEvent(headers)


def make_token(role="user", sub="1", secret=SECRET, **overrides):
    payload = {"sub": sub, "email": "alice@example.com", "role": role, **overrides}
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)


def test_require_auth_accepts_valid_bearer_token():
    token = make_token(role="moderator", sub="42")
    app = FakeApp(headers={"Authorization": f"Bearer {token}"})

    user = auth_middleware.require_auth(app)

    assert user["sub"] == "42"
    assert user["role"] == "moderator"


def test_require_auth_is_case_insensitive_header_lookup():
    # Mirrors powertools' CaseInsensitiveDict behavior for real events.
    token = make_token()
    app = FakeApp(headers={"authorization": f"Bearer {token}"})

    user = auth_middleware.require_auth(app)

    assert user["sub"] == "1"


def test_require_auth_rejects_missing_header():
    app = FakeApp(headers={})

    with pytest.raises(UnauthorizedError):
        auth_middleware.require_auth(app)


def test_require_auth_rejects_missing_bearer_prefix():
    token = make_token()
    app = FakeApp(headers={"Authorization": token})

    with pytest.raises(UnauthorizedError):
        auth_middleware.require_auth(app)


def test_require_auth_rejects_bad_signature():
    token = make_token(secret="wrong-secret")
    app = FakeApp(headers={"Authorization": f"Bearer {token}"})

    with pytest.raises(UnauthorizedError):
        auth_middleware.require_auth(app)


def test_require_auth_rejects_expired_token():
    token = jwt.encode(
        {"sub": "1", "email": "a@b.com", "role": "user", "iat": 0, "exp": 1},
        SECRET,
        algorithm="HS256",
    )
    app = FakeApp(headers={"Authorization": f"Bearer {token}"})

    with pytest.raises(UnauthorizedError):
        auth_middleware.require_auth(app)


def test_require_role_allows_matching_role():
    auth_middleware.require_role({"role": "moderator"}, "moderator")


def test_require_role_rejects_wrong_role():
    with pytest.raises(ForbiddenError):
        auth_middleware.require_role({"role": "user"}, "moderator")


def test_require_owner_or_moderator_allows_owner():
    auth_middleware.require_owner_or_moderator({"sub": "5", "role": "user"}, owner_id=5)


def test_require_owner_or_moderator_allows_moderator_for_any_owner():
    auth_middleware.require_owner_or_moderator({"sub": "999", "role": "moderator"}, owner_id=5)


def test_require_owner_or_moderator_rejects_non_owner_non_moderator():
    with pytest.raises(ForbiddenError):
        auth_middleware.require_owner_or_moderator({"sub": "999", "role": "user"}, owner_id=5)
