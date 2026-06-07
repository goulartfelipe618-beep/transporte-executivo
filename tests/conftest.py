import os

import pytest
from httpx import ASGITransport, AsyncClient

# Minimal env for tests before app import
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-chars")
os.environ.setdefault("CSRF_SECRET_KEY", "test-csrf-secret-key-minimum-32-chars")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://nexus:nexus_dev_password@localhost:5432/motor_reservas",
)

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
