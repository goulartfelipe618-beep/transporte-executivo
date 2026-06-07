"""Cliente HTTP para o Gateway do Sistema Master (porta 8770)."""

from typing import Any, Optional

import httpx

from app.config import get_settings


class GatewayAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def normalize_vehicle(raw: dict[str, Any]) -> dict[str, Any]:
    raw = dict(raw or {})
    price = raw.get("price") or raw.get("preco_base") or raw.get("valor_estimado") or 0
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = 0.0
    brand = str(raw.get("brand") or raw.get("marca") or "").strip()
    model = str(raw.get("model") or raw.get("modelo") or "").strip()
    plate = str(raw.get("plate") or raw.get("placa") or "").strip()
    name = str(raw.get("name") or raw.get("display_name") or "").strip()
    if not name:
        name = f"{brand} {model}".strip()
    return {
        "id": str(raw.get("id") or raw.get("id_admin") or ""),
        "category": raw.get("category") or raw.get("categoria") or raw.get("tipo_veiculo") or "",
        "name": name,
        "brand": brand or None,
        "model": model or None,
        "plate": plate or None,
        "image_url": raw.get("image_url") or raw.get("foto") or raw.get("imagem"),
        "passengers": int(raw.get("passengers") or raw.get("capacidade") or 3),
        "luggage": int(raw.get("luggage") or raw.get("bagagens") or 3),
        "price": price,
        "cidade": raw.get("cidade"),
        "estado": raw.get("estado"),
    }


class GatewayAPIClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.gateway_api_base_url).rstrip("/")
        self.api_key = api_key or settings.gateway_api_key
        self.timeout = timeout or settings.gateway_api_timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _network_base(self, slug: str, codigo: str) -> str:
        return f"/api/v1/network/{slug}/{codigo}"

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
                raise GatewayAPIError(
                    f"Gateway error: {e.response.status_code}",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise GatewayAPIError(f"Gateway connection failed: {e}") from e

    async def get_network(self, slug: str, codigo: str) -> dict[str, Any]:
        data = await self._request("GET", self._network_base(slug, codigo))
        return data if isinstance(data, dict) else {"data": data}

    async def get_vehicles(
        self,
        slug: str,
        codigo: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        result = await self._request(
            "GET",
            f"{self._network_base(slug, codigo)}/vehicles",
            params=params or {},
        )
        if isinstance(result, list):
            items = result
        else:
            items = result.get("items", result.get("vehicles", []))
        return [normalize_vehicle(v) for v in items if isinstance(v, dict)]

    async def post_quote(self, slug: str, codigo: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._request(
            "POST",
            f"{self._network_base(slug, codigo)}/quote",
            json=payload,
        )
        return result if isinstance(result, dict) else {"quote": result}

    async def post_reserve(self, slug: str, codigo: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self._request(
            "POST",
            f"{self._network_base(slug, codigo)}/reserve",
            json=payload,
        )
        return result if isinstance(result, dict) else {"reservation": result}
