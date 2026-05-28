"""
services/supabase_client.py
---------------------------
Singleton Supabase client using the service-role key.

The service-role key bypasses Row Level Security, which is what we want
on the backend — RLS only applies to client-side requests made with the
anon key. The backend is already protected by our own JWT middleware.

Never expose the service key to the frontend.
"""

from functools import lru_cache
from supabase import Client, create_client
from app.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Return (and cache) a single Supabase service-role client."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)
