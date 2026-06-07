from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class TripTypeEnum(str, Enum):
    ONE_WAY = "one_way"
    ROUND_TRIP = "round_trip"
    HOURLY = "hourly"


class SearchRequest(BaseModel):
    trip_type: TripTypeEnum = TripTypeEnum.ONE_WAY
    origin: Optional[str] = Field(None, max_length=512)
    destination: Optional[str] = Field(None, max_length=512)
    city: Optional[str] = Field(None, max_length=255)
    trip_date: date
    trip_time: time
    return_date: Optional[date] = None
    return_time: Optional[time] = None
    hourly_hours: Optional[int] = Field(None, ge=4, le=12)
    passengers: int = Field(default=1, ge=1, le=50)
    luggage: int = Field(default=0, ge=0, le=50)
    notes: Optional[str] = Field(None, max_length=2000)
    return_trip: bool = False

    @model_validator(mode="after")
    def validate_trip_fields(self):
        if self.trip_type == TripTypeEnum.HOURLY:
            if not self.city:
                raise ValueError("Cidade é obrigatória para serviço por hora")
            if not self.hourly_hours:
                raise ValueError("Quantidade de horas é obrigatória")
        else:
            if not self.origin or len(self.origin.strip()) < 3:
                raise ValueError("Origem é obrigatória")
            if not self.destination or len(self.destination.strip()) < 3:
                raise ValueError("Destino é obrigatório")
            if self.trip_type == TripTypeEnum.ROUND_TRIP:
                if not self.return_date or not self.return_time:
                    raise ValueError("Data e horário de volta são obrigatórios")
        return self


class VehicleSelectRequest(BaseModel):
    category: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    benefits: list[str] = []


class PassengerRequest(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=255)
    phone: str = Field(..., min_length=8, max_length=32)
    whatsapp: Optional[str] = Field(None, max_length=32)
    email: EmailStr
    cpf: str = Field(..., min_length=11, max_length=14)
    company: Optional[str] = Field(None, max_length=255)
    flight_number: Optional[str] = Field(None, max_length=32)
    notes: Optional[str] = Field(None, max_length=2000)
    lgpd_accepted: bool = False

    @model_validator(mode="after")
    def validate_lgpd(self):
        if not self.lgpd_accepted:
            raise ValueError("É necessário aceitar os termos de privacidade (LGPD)")
        return self


class PaymentRequest(BaseModel):
    provider: str = Field(..., pattern="^(mercadopago|stripe|pix|corporate)$")
    method: str = Field(..., pattern="^(card|pix|boleto|invoice)$")


class ReservationResponse(BaseModel):
    id: UUID
    code: str
    status: str
    trip_type: Optional[str] = None
    origin: str
    destination: str
    trip_date: date
    trip_time: time
    total_amount: Optional[Decimal] = None
    vehicle_name: Optional[str] = None
    distance_km: Optional[Decimal] = None
    duration_minutes: Optional[int] = None

    model_config = {"from_attributes": True}
