"""Shared Supabase client utility."""
from __future__ import annotations

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get singleton Supabase client from environment variables.
    
    Uses LRU cache to ensure only one client instance is created.
    This is safe because Supabase clients are thread-safe.
    
    Returns:
        Supabase Client instance
        
    Raises:
        RuntimeError: If Supabase URL or key not configured
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase URL or key not configured in environment.")
    return create_client(url, key)

