import pytest
from unittest.mock import AsyncMock, patch

from app.clients.master_api import MasterAPIClient, MasterAPIError


@pytest.mark.asyncio
async def test_get_stats_fallback_on_error():
    client = MasterAPIClient(base_url="http://invalid.test", api_key="test")
    with patch.object(client, "_request", side_effect=MasterAPIError("fail")):
        with pytest.raises(MasterAPIError):
            await client.get_stats()


@pytest.mark.asyncio
async def test_get_vehicles_parses_list():
    client = MasterAPIClient()
    mock_response = [{"category": "sedan", "name": "Sedan", "price": 100}]
    with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_response):
        result = await client.get_vehicles("A", "B")
        assert len(result) == 1
        assert result[0]["category"] == "sedan"
