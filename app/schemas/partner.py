from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.partner import PartnerType


class PartnerPublic(BaseModel):
    external_id: str
    name: str
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    partner_type: PartnerType

    model_config = {"from_attributes": True}


class PartnerCreate(BaseModel):
    external_id: str
    name: str
    slug: str
    token: str
    partner_type: PartnerType = PartnerType.AFFILIATE
    commission_percent: Decimal = Decimal("10.00")
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None


class PartnerLogin(BaseModel):
    email: EmailStr
    password: str


class PartnerDashboardStats(BaseModel):
    total_reservations: int
    total_sold: Decimal
    total_commissions: Decimal
    pending_commissions: Decimal
