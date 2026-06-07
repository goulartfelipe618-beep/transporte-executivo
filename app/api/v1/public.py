"""Public API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.master_api import MasterAPIClient, MasterAPIError
from app.database import get_db

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/stats")
async def get_stats():
    client = MasterAPIClient()
    try:
        return await client.get_stats()
    except MasterAPIError:
        return {"status": "ok", "source": "engine", "partners_active": 0, "reservations_today": 0}


@router.get("/coverage")
async def get_coverage():
    client = MasterAPIClient()
    try:
        return await client.get_coverage()
    except MasterAPIError:
        return {"regions": [], "source": "engine_fallback"}


@router.get("/locations")
async def get_locations(q: Optional[str] = Query(None, min_length=2)):
    client = MasterAPIClient()
    try:
        return {"items": await client.get_locations(q)}
    except MasterAPIError:
        fallback = [
            {"name": "Aeroporto Internacional de Guarulhos (GRU)", "type": "aeroporto"},
            {"name": "Aeroporto Santos Dumont (SDU)", "type": "aeroporto"},
            {"name": "Hotel Copacabana Palace", "type": "hotel"},
            {"name": "Centro de Convenções Expo Center Norte", "type": "evento"},
        ]
        if q:
            q_lower = q.lower()
            fallback = [i for i in fallback if q_lower in i["name"].lower()]
        return {"items": fallback}


@router.get("/vehicles")
async def get_vehicles(
    origin: str = Query(...),
    destination: str = Query(...),
    passengers: int = Query(1, ge=1),
    luggage: int = Query(0, ge=0),
):
    from app.services.booking_service import get_available_vehicles

    items = await get_available_vehicles(origin, destination, passengers, luggage)
    return {"items": items}
