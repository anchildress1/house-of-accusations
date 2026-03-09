"""Supabase client initialization."""

from functools import lru_cache

from supabase import Client, create_client

from house_of_accusations.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Anon client for player-facing operations."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache(maxsize=1)
def get_supabase_service_client() -> Client:
    """Service-role client for server-side AI evaluation (accesses evidence_full view)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
