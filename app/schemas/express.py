"""Schemas do fluxo Express."""

from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ExpressStartRequest(BaseModel):
    trip_type: Literal["one_way", "round_trip", "hourly"] = "one_way"
    origin: str = Field(..., min_length=2, max_length=512)
    destination: str = Field(..., min_length=2, max_length=512)
    trip_date: date
    trip_time: time
    passenger_name: str = Field(..., min_length=2, max_length=255)
    passenger_whatsapp: str = Field(..., min_length=8, max_length=32)
    return_date: Optional[date] = None
    return_time: Optional[time] = None
    hourly_hours: Optional[int] = Field(None, ge=1, le=24)
    slug: Optional[str] = None
    codigo: Optional[str] = None
    contributor_ref: Optional[str] = None


class ExpressVehicleSelectRequest(BaseModel):
    vehicle_id: str
    category: str
    name: str
    image_url: Optional[str] = None
    passengers: int = 1
    luggage: int = 0
    price: float


class ExpressConfirmRequest(BaseModel):
    lgpd_accepted: bool = False
    passenger_name: Optional[str] = None
    passenger_whatsapp: Optional[str] = None


class ExpressStartResponse(BaseModel):
    reservation_id: str
    quote_id: Optional[str] = None
    redirect_url: str


class ExpressConfirmResponse(BaseModel):
    reservation_code: str
    redirect_url: str
    whatsapp_url: Optional[str] = None
    message: str = "Sua solicitação foi enviada com sucesso."


class NetworkContextResponse(BaseModel):
    network: dict
    is_hotel: bool
    default_origin: str
    contributor_ref: Optional[str] = None
