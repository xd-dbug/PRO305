import importlib.util
from pathlib import Path

import jwt

MODULE_PATH = Path(__file__).parent.parent / "auth_service.py"


def _load():
    spec = importlib.util.spec_from_file_location("auth_service", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auth_service = _load()


def test_hash_password_produces_verifiable_hash():
    hashed = auth_service.hash_password("correct-horse")
    assert auth_service.verify_password("correct-horse", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = auth_service.hash_password("correct-horse")
    assert auth_service.verify_password("wrong-password", hashed) is False


def test_issue_token_contains_expected_claims():
    token = auth_service.issue_token(1, "alice@example.com", "user", secret="test-secret", expires_in=3600)
    decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
    assert decoded["sub"] == "1"
    assert decoded["email"] == "alice@example.com"
    assert decoded["role"] == "user"
    assert decoded["exp"] > decoded["iat"]
