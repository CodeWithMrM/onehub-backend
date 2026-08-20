"""
Clerk session token verification.

The Expo apps send `Authorization: Bearer <clerk-session-token>`.
We verify it against Clerk's JWKS (fetched from
`{CLERK_JWT_ISSUER}/.well-known/jwks.json` and cached in-process)
rather than trusting anything the client claims about itself.

This module only verifies tokens and returns the decoded claims.
Turning those claims into a local `User` row is the job of
`user_service.py`, wired up through `core/dependencies.py`.
"""

import time
from typing import Any, Dict

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import settings
from app.core.errors import UnauthorizedError

_jwk_client: PyJWKClient | None = None
_jwk_client_created_at: float = 0
_JWK_CLIENT_TTL_SECONDS = 3600


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client, _jwk_client_created_at
    now = time.time()
    if _jwk_client is None or (now - _jwk_client_created_at) > _JWK_CLIENT_TTL_SECONDS:
        if not settings.CLERK_JWT_ISSUER:
            raise UnauthorizedError("Authentication is not configured on the server.")
        jwks_url = f"{settings.CLERK_JWT_ISSUER.rstrip('/')}/.well-known/jwks.json"
        _jwk_client = PyJWKClient(jwks_url)
        _jwk_client_created_at = now
    return _jwk_client


def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Clerk session JWT's signature, issuer, and expiry.
    Returns the decoded claims on success. Raises UnauthorizedError
    on any failure — never partially trust a token.
    """
    if not token:
        raise UnauthorizedError("Missing authentication token.")

    try:
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.CLERK_JWT_ISSUER,
            options={"verify_aud": False},
        )
        return claims
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Your session has expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token.") from exc
    except httpx.HTTPError as exc:
        raise UnauthorizedError("Could not verify authentication token.") from exc
