"""Testes alinhamento handoff Gateway 2026.07.20."""

import pytest

from app.clients.gateway_api import GatewayAPIClient, normalize_vehicle
from app.config import get_settings


def test_no_mock_vehicles_in_module():
    import app.clients.gateway_api as mod

    assert not hasattr(mod, "_mock_vehicles")
    assert not hasattr(mod, "DEV_NETWORK_MOCKS")


def test_mock_fallback_disabled():
    get_settings.cache_clear()
    assert get_settings().gateway_mock_fallback is False


@pytest.mark.asyncio
async def test_vehicles_network_path(monkeypatch):
    client = GatewayAPIClient()
    seen: dict = {}

    async def fake_request(method, path, **kwargs):
        seen["path"] = path
        return []

    monkeypatch.setattr(client, "_request", fake_request)
    await client.get_vehicles("hotel-blumenau", "2C9HGU", {"origin": "A"})
    assert seen["path"] == "/api/v1/network/hotel-blumenau/2C9HGU/vehicles"


@pytest.mark.asyncio
async def test_reserve_network_path(monkeypatch):
    client = GatewayAPIClient()
    seen: dict = {}

    async def fake_request(method, path, **kwargs):
        seen["path"] = path
        seen["json"] = kwargs.get("json")
        return {"reservation_code": "NX1", "reservation_id": "m1"}

    monkeypatch.setattr(client, "_request", fake_request)
    await client.post_reserve("hotel-blumenau", "2C9HGU", {"quote_id": "q1"})
    assert seen["path"] == "/api/v1/network/hotel-blumenau/2C9HGU/reserve"


def test_normalize_vehicle_no_local_invention():
    v = normalize_vehicle({"id": "v99", "category": "SUV", "price": 400})
    assert v["id"] == "v99"
    assert v["price"] == 400.0
