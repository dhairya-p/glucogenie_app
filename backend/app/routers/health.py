"""Health check endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from app.dependencies import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Simple health check response."""

    api: str
    supabase: bool


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Basic liveness endpoint to verify the API and Supabase connectivity.",
)
async def health(
    supabase: Client = Depends(get_supabase),
) -> HealthResponse:
    """Simple health check endpoint.

    - Verifies the API is running.
    - Performs a lightweight call to Supabase auth to ensure configuration is valid.
    """
    supabase_ok = True
    try:
        # Perform a lightweight query to verify Supabase connection.
        # Try to query a common table (profiles) with limit 0 to minimize overhead.
        _ = supabase.table("profiles").select("id").limit(0).execute()
    except Exception as exc:  # noqa: BLE001
        supabase_ok = False
        logger.error("Supabase health check failed: %s", exc)

    return HealthResponse(api="ok", supabase=supabase_ok)
