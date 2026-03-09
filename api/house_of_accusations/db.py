"""Supabase client initialization."""

from functools import lru_cache

from supabase import Client, create_client

from house_of_accusations.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
