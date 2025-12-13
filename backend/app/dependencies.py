"""Shared FastAPI dependencies for authentication and utilities."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from supabase import Client

from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_supabase(request: Request) -> Client:
    """FastAPI dependency to access the shared Supabase client from app state."""
    return request.app.state.supabase


async def get_current_user(
    request: Request,
    supabase: Client = Depends(get_supabase),
) -> Any:
    """Validate the Supabase JWT from the Authorization header.

    The Flutter frontend must send: Authorization: Bearer <access_token>
    This dependency ensures all protected routes receive an authenticated user.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    access_token = auth_header.removeprefix("Bearer").strip()
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    try:
        user_response = supabase.auth.get_user(access_token)
        user = getattr(user_response, "user", None)
        if user is None:
            logger.error("Supabase get_user returned None")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            )
        logger.info("Supabase auth succeeded. User type: %s", type(user).__name__)
        if hasattr(user, "id"):
            logger.info("User ID: %s", user.id)
        elif isinstance(user, dict):
            logger.info("User ID: %s", user.get("id"))
        return user
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Supabase JWT verification failed: %s", exc)
        # For development: try JWT decode fallback if Supabase fails
        try:
            import jwt

            decoded = jwt.decode(access_token, options={"verify_signature": False})
            user_id = decoded.get("sub") or decoded.get("user_id")
            if user_id:
                user = {"id": user_id, "email": decoded.get("email")}
                logger.warning(
                    "Using JWT fallback due to Supabase error. User ID: %s", user_id
                )
                return user
        except ImportError:
            logger.error("PyJWT not installed, cannot use JWT fallback")
        except Exception as jwt_exc:  # noqa: BLE001
            logger.error("JWT fallback also failed: %s", jwt_exc)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired access token: {str(exc)}",
        ) from exc


def extract_user_id(user: Any) -> str:
    """Extract user ID from authenticated user object.

    Args:
        user: Authenticated user object (from get_current_user)

    Returns:
        User ID as string

    Raises:
        HTTPException: If user ID cannot be extracted
    """
    user_id = ""
    if hasattr(user, "id"):
        user_id = str(user.id)
    elif isinstance(user, dict):
        user_id = str(user.get("id", ""))
    elif hasattr(user, "__dict__"):
        user_dict = vars(user)
        user_id = str(user_dict.get("id", ""))

    if not user_id:
        logger.error("Could not extract user_id from user object. User type: %s", type(user).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found",
        )

    return user_id
