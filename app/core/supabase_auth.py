"""Supabase access token verification helpers for FastAPI.

Supports both legacy symmetric JWT verification and the newer Supabase signing
key setups by falling back to the Auth API when local verification is not
possible.
"""

from __future__ import annotations

import json
import logging
from urllib import error, request
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SupabaseAuthError(Exception):
    """Raised when Supabase JWT verification fails."""


def verify_supabase_token(token: str) -> dict[str, Any]:
    """Decode and verify a Supabase-issued JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dict containing at minimum ``sub`` (user UUID).

    Raises:
        SupabaseAuthError: If the token is invalid, expired, or Supabase Auth
            could not verify it.
    """
    settings = get_settings()
    unverified = _decode_unverified(token)

    # Legacy symmetric projects can still be verified locally with the JWT secret.
    if settings.supabase_jwt_secret and _uses_hs256(token):
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "require": ["sub", "exp", "aud"],
                },
            )
            _validate_subject(payload)
            return payload
        except InvalidTokenError as exc:
            logger.debug("supabase_local_jwt_verification_failed: %s", exc)

    # Newer Supabase projects commonly use signing keys that cannot be verified
    # with SUPABASE_JWT_SECRET alone, so ask Supabase Auth to validate the token.
    user = _fetch_supabase_user(token)
    user_id = user.get("id")
    if not user_id or not isinstance(user_id, str):
        raise SupabaseAuthError("Supabase Auth returned no valid user id.")

    payload = dict(unverified)
    payload["sub"] = user_id
    if isinstance(user.get("email"), str):
        payload["email"] = user["email"]
    return payload


def is_supabase_token(token: str) -> bool:
    """Heuristic check: does this look like a Supabase-issued JWT?

    Supabase tokens have an ``aud`` claim of ``"authenticated"`` and a UUID
    ``sub`` claim.  Legacy app tokens use an integer or email as ``sub``.
    """
    try:
        unverified = _decode_unverified(token)
        audience = unverified.get("aud")
        if isinstance(audience, str):
            return audience == "authenticated"
        if isinstance(audience, list):
            return "authenticated" in audience
        return False
    except Exception:
        return False


def _decode_unverified(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, options={"verify_signature": False})
    if not isinstance(payload, dict):
        raise SupabaseAuthError("Token payload is not an object.")
    return payload


def _uses_hs256(token: str) -> bool:
    try:
        header = jwt.get_unverified_header(token)
    except Exception:
        return True
    return header.get("alg") == "HS256"


def _validate_subject(payload: dict[str, Any]) -> None:
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise SupabaseAuthError("Token missing valid 'sub' claim")


def _fetch_supabase_user(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.supabase_url:
        raise SupabaseAuthError("SUPABASE_URL is not configured")

    api_key = settings.supabase_anon_key or settings.supabase_service_role_key
    if not api_key:
        raise SupabaseAuthError("Supabase API key is not configured")

    req = request.Request(
        url=f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": api_key,
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        logger.debug("supabase_auth_http_error status=%s", exc.code)
        raise SupabaseAuthError("Supabase Auth rejected the access token.") from exc
    except error.URLError as exc:
        raise SupabaseAuthError("Could not reach Supabase Auth.") from exc

    try:
        payload = json.loads(body)
    except Exception as exc:
        raise SupabaseAuthError("Supabase Auth returned an invalid response.") from exc
    if not isinstance(payload, dict):
        raise SupabaseAuthError("Supabase Auth returned an invalid payload.")
    return payload
