import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "motor-reservas-nexus" in data["service"]


@pytest.mark.asyncio
async def test_health_probe_127_production():
    os.environ["APP_ENV"] = "production"
    os.environ["ALLOWED_HOSTS"] = "api.transporteexecutivo.com"
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health", headers={"Host": "127.0.0.1:8000"})
    assert response.status_code == 200
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_home_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Nexus Transfer" in response.text
