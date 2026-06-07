"""Desacoplado HTTP client para o Sistema Master.

O Motor de Reservas NUNCA acessa app_state.json, Portal Empresa ou Portal Motorista.
Toda comunicação ocorre via API REST.
"""

from typing import Any, Optional

import httpx

from app.config import get_settings


class MasterAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class MasterAPIClient:
    """Cliente HTTP para integração com Sistema Master."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.master_api_base_url).rstrip("/")
        self.api_key = api_key or settings.master_api_key
        self.timeout = timeout or settings.master_api_timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(method, url, headers=self._headers(), **kwargs)
                response.raise_for_status()
                if response.status_code == 204:
                    return None
                return response.json()
            except httpx.HTTPStatusError as e:
                raise MasterAPIError(
                    f"Master API error: {e.response.status_code}",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise MasterAPIError(f"Master API connection failed: {e}") from e

    async def get_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/public/stats")

    async def get_coverage(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/public/coverage")

    async def get_locations(self, query: Optional[str] = None) -> list[dict[str, Any]]:
        params = {"q": query} if query else {}
        result = await self._request("GET", "/api/v1/public/locations", params=params)
        return result if isinstance(result, list) else result.get("items", [])

    async def get_vehicles(
        self,
        origin: str,
        destination: str,
        passengers: int = 1,
        luggage: int = 0,
    ) -> list[dict[str, Any]]:
        params = {
            "origin": origin,
            "destination": destination,
            "passengers": passengers,
            "luggage": luggage,
        }
        result = await self._request("GET", "/api/v1/public/vehicles", params=params)
        return result if isinstance(result, list) else result.get("items", [])

    async def send_reservation_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/webhooks/inbound/reservation.request",
            json=payload,
        )
