"""Root conftest for API tests.

Env vars must be set before main.py is imported because get_settings()
runs at module level. Using os.environ.setdefault preserves real values
when a .env file or CI secrets are present.
"""

import os
from collections.abc import AsyncGenerator

# Set required secrets before main.py triggers get_settings()
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")

import pytest
from httpx import ASGITransport, AsyncClient

from house_of_accusations.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
