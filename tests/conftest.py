import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["APP_ENV"] = "development"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-minimum-32-chars"
os.environ["CSRF_SECRET_KEY"] = "test-csrf-secret-key-minimum-32-chars"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@db.xxxxx.supabase.co:5432/postgres",
)

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
