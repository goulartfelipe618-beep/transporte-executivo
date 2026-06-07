import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "motor-reservas-nexus" in data["service"]


@pytest.mark.asyncio
async def test_home_page(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Nexus Transfer" in response.text
