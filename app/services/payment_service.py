"""Payment gateway integration stubs (Mercado Pago, Stripe, PIX)."""

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from app.config import get_settings

settings = get_settings()


class PaymentGatewayError(Exception):
    pass


async def create_mercadopago_checkout(
    reservation_id: UUID,
    amount: Decimal,
    description: str,
) -> dict[str, Any]:
    if not settings.mercadopago_access_token:
        return {
            "provider": "mercadopago",
            "status": "sandbox",
            "checkout_url": f"/booking/{reservation_id}/payment?provider=mercadopago",
            "message": "Configure MERCADOPAGO_ACCESS_TOKEN para produção",
        }
    # Production: httpx POST to Mercado Pago API
    raise NotImplementedError("Integração Mercado Pago em produção pendente de credenciais")


async def create_stripe_checkout(
    reservation_id: UUID,
    amount: Decimal,
    description: str,
) -> dict[str, Any]:
    if not settings.stripe_secret_key:
        return {
            "provider": "stripe",
            "status": "sandbox",
            "checkout_url": f"/booking/{reservation_id}/payment?provider=stripe",
        }
    raise NotImplementedError("Integração Stripe em produção pendente de credenciais")


async def create_pix_charge(
    reservation_id: UUID,
    amount: Decimal,
) -> dict[str, Any]:
    return {
        "provider": "pix",
        "status": "pending",
        "qr_code_text": f"PIX-NEXUS-{reservation_id}",
        "expires_in": 3600,
    }
