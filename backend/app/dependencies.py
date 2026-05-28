"""
dependencies.py
---------------
FastAPI dependency-injection helpers.

get_current_user:  verifies the Supabase JWT sent in the Authorization header
                   and returns a minimal user dict {user_id, email}.
get_db:            yields a Supabase client scoped to the current request.

Usage in a router:
    @router.get("/me")
    async def me(user = Depends(get_current_user), db = Depends(get_db)):
        ...
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings
from app.services.supabase_client import get_supabase_client

_bearer = HTTPBearer(auto_error=True)


import urllib.request
import json

_jwks = None

def get_jwks(supabase_url: str) -> dict:
    global _jwks
    if _jwks is None:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        req = urllib.request.Request(jwks_url)
        with urllib.request.urlopen(req) as response:
            _jwks = json.loads(response.read())
    return _jwks

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:
    """
    Verify a Supabase-issued JWT and return the decoded user payload.

    Validates asymmetric JWTs (RS256/ES256) using the Supabase JWKS endpoint.
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        jwks = get_jwks(settings.supabase_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auth configuration error (failed to fetch JWKS): {e}"
        )

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        if alg == "HS256":
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                issuer=f"{settings.supabase_url}/auth/v1",
            )
        else:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256", "ES256"],
                audience="authenticated",
                issuer=f"{settings.supabase_url}/auth/v1",
            )
    except JWTError as exc:
        print(f"[DEBUG AUTH ERROR] JWTError: {exc}")
        try:
            unverified = jwt.get_unverified_claims(token)
            print(f"[DEBUG AUTH] Unverified claims: {unverified}")
        except Exception as e:
            print(f"[DEBUG AUTH] Could not decode claims: {e}")
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )

    return {
        "user_id": user_id,
        "email": payload.get("email", ""),
        "role": payload.get("role", "authenticated"),
    }


def get_db():
    """Yield a shared Supabase client. Stateless — safe to reuse across requests."""
    yield get_supabase_client()


# Convenience type aliases for cleaner router signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]
DB = Annotated[object, Depends(get_db)]
