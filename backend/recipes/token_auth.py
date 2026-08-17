"""
JWT auth helper, local to the recipes function for now.

The shared layer (backend/layer/shared/) only has db.py and responses.py —
no auth helper exists there yet. Mealplan will need identical logic
(auth-required routes too), so this probably belongs in shared/auth.py
eventually. Keeping it local to recipes for now rather than modifying the
shared layer unprompted — that's Zeke's territory per the proposal, and a
layer change affects every function, not just this one. Worth a quick
sync with him before duplicating this a second time in mealplan.

Requires PyJWT — added to backend/recipes/requirements.txt (not the shared
layer, so this doesn't affect auth/mealplan's dependencies).
"""
import os
import jwt
from aws_lambda_powertools.event_handler.exceptions import UnauthorizedError, ForbiddenError


def get_current_user(event) -> dict:
    """Extract and verify the bearer token from an APIGatewayRestResolver event.

    Returns {"user_id": str, "role": "User" | "Moderator"}.
    """
    auth_header = event.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise UnauthorizedError(f"Invalid token: {e}")

    user_id = payload.get("userId") or payload.get("sub")
    role = payload.get("role")
    if not user_id or role not in ("User", "Moderator"):
        raise UnauthorizedError("Token missing required claims")

    return {"user_id": str(user_id), "role": role}


def require_owner_or_moderator(user: dict, resource_author_id) -> None:
    """403s unless the caller authored the resource or is a Moderator."""
    if user["role"] != "Moderator" and str(user["user_id"]) != str(resource_author_id):
        raise ForbiddenError("Not the recipe author or a Moderator")