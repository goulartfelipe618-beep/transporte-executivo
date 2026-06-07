"""Cliente Supabase — PostgREST + RPC (projeto Master)."""

from typing import Any, Optional

import httpx

from app.config import get_settings


class SupabaseError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SupabaseClient:
    def __init__(self) -> None:
        settings = get_settings()
        base = (settings.supabase_url or "").rstrip("/")
        self.rpc_url = f"{base}/rest/v1/rpc" if base else ""
        self.api_key = settings.supabase_anon_key or ""
        self.enabled = bool(base and self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def rpc(self, name: str, payload: Optional[dict[str, Any]] = None) -> Any:
        if not self.enabled:
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    f"{self.rpc_url}/{name}",
                    headers=self._headers(),
                    json=payload or {},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise SupabaseError(
                    f"Supabase RPC {name}: {e.response.status_code}",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise SupabaseError(f"Supabase connection failed: {e}") from e
