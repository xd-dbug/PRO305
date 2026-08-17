"""JWT verification and role enforcement for protected API routes.

Shared across Lambda functions via the layer (see backend/layer/). Verifies the
bearer token issued by POST /auth/login (backend/auth/auth_service.issue_token)
and exposes helpers for gating routes by role or resource ownership. Nothing in
here talks to the DB — the token payload (sub/email/role) is trusted once the
signature and expiry check out.
"""

import os

from aws_lambda_powertools.event_handler.exceptions import ForbiddenError, UnauthorizedError
import jwt

BEARER_PREFIX = "Bearer "


def require_auth(app):
    """Verify the `Authorization: Bearer <jwt>` header on the current request.

    Returns the decoded token payload (sub, email, role, iat, exp) on success.
    Raises UnauthorizedError (401) if the header is missing/malformed or the
    token is missing, invalid, or expired.
    """
    auth_header = app.current_event.headers.get("Authorization") or ""
    if not auth_header.startswith(BEARER_PREFIX):
        raise UnauthorizedError("missing or malformed Authorization header")

    token = auth_header[len(BEARER_PREFIX) :].strip()
    if not token:
        raise UnauthorizedError("missing bearer token")

    try:
        return jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
    except jwt.PyJWTError:
        raise UnauthorizedError("invalid or expired token")


def require_role(user, *allowed_roles):
    """Ensure the authenticated user's role is one of allowed_roles.

    `user` is the payload returned by require_auth(). Raises ForbiddenError
    (403) if the role isn't allowed.
    """
    if user.get("role") not in allowed_roles:
        raise ForbiddenError("insufficient role for this action")


def require_owner_or_moderator(user, owner_id):
    """Ensure the authenticated user owns the resource or is a moderator.

    `user` is the payload returned by require_auth(). Raises ForbiddenError
    (403) if the user is neither the resource's owner (matched against the
    token's `sub`) nor a moderator.
    """
    if user.get("role") == "moderator":
        return
    if str(user.get("sub")) != str(owner_id):
        raise ForbiddenError("must be the resource owner or a moderator")
