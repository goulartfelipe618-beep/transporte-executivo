"""Armazenamento em memória — fluxo Express sem PostgreSQL obrigatório."""

from __future__ import annotations

import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal
from typing import Any, Optional


def _new_code() -> str:
    return "NX" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


@dataclass
class ExpressReservation:
    id: str
    code: str
    status: str = "search"
    slug: str = ""
    codigo: str = ""
    network_name: str = ""
    network_type: str = ""
    network_city: str = ""
    network_estado: str = ""
    commission_percent: Optional[float] = None
    trip_type: str = "one_way"
    origin: str = ""
    destination: str = ""
    trip_date: date = field(default_factory=date.today)
    trip_time: time = field(default_factory=lambda: time(10, 0))
    return_trip: bool = False
    return_date: Optional[date] = None
    return_time: Optional[time] = None
    hourly_hours: Optional[int] = None
    passengers: int = 1
    luggage: int = 1
    passenger_name: str = ""
    passenger_whatsapp: str = ""
    contributor_ref: Optional[str] = None
    quote_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    vehicle_category: Optional[str] = None
    vehicle_name: Optional[str] = None
    vehicle_image_url: Optional[str] = None
    subtotal: float = 0.0
    taxes_amount: float = 0.0
    total_amount: float = 0.0
    gateway_result: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, **kwargs: Any) -> ExpressReservation:
        rid = str(uuid.uuid4())
        return cls(id=rid, code=_new_code(), **kwargs)


_STORE: dict[str, ExpressReservation] = {}


def save(reservation: ExpressReservation) -> ExpressReservation:
    _STORE[reservation.id] = reservation
    return reservation


def get(reservation_id: str) -> Optional[ExpressReservation]:
    return _STORE.get(reservation_id)


def calculate_totals(reservation: ExpressReservation, base_price: float) -> None:
    price = Decimal(str(base_price))
    if reservation.trip_type == "hourly" and reservation.hourly_hours:
        price = price * Decimal(reservation.hourly_hours) / Decimal("4")
    elif reservation.return_trip or reservation.trip_type == "round_trip":
        price *= Decimal("1.8")
    taxes = (price * Decimal("0.05")).quantize(Decimal("0.01"))
    total = (price + taxes).quantize(Decimal("0.01"))
    reservation.subtotal = float(price.quantize(Decimal("0.01")))
    reservation.taxes_amount = float(taxes)
    reservation.total_amount = float(total)
