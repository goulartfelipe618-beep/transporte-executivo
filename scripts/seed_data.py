"""Seed initial admin, partner and partner user for development."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.partner import Partner, PartnerType, PartnerUser
from app.models.user import AdminUser
from app.security.password import hash_password


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        partner = (await db.execute(select(Partner).where(Partner.external_id == "net-000001"))).scalar_one_or_none()
        if not partner:
            partner = Partner(
                external_id="net-000001",
                name="Hotel Demo Parceiro",
                slug="hotel-demo",
                token="a8x72mkq9",
                partner_type=PartnerType.HOTEL,
                commission_percent=10,
                active=True,
                logo_url="https://via.placeholder.com/120x40?text=Hotel+Demo",
                banner_url="https://via.placeholder.com/800x200?text=Banner",
            )
            db.add(partner)
            await db.flush()
            print(f"Partner criado: {partner.external_id}/{partner.token}")

        admin = (await db.execute(select(AdminUser).where(AdminUser.email == "admin@nexus.local"))).scalar_one_or_none()
        if not admin:
            admin = AdminUser(
                email="admin@nexus.local",
                password_hash=hash_password("Admin@123"),
                full_name="Administrador Nexus",
                role="superadmin",
            )
            db.add(admin)
            print("Admin: admin@nexus.local / Admin@123")

        pu = (await db.execute(select(PartnerUser).where(PartnerUser.email == "parceiro@demo.local"))).scalar_one_or_none()
        if not pu and partner:
            pu = PartnerUser(
                partner_id=partner.id,
                email="parceiro@demo.local",
                password_hash=hash_password("Parceiro@123"),
                full_name="Usuário Parceiro Demo",
            )
            db.add(pu)
            print("Parceiro: parceiro@demo.local / Parceiro@123")

        await db.commit()
    print("Seed concluído.")
    print("Link de teste: http://localhost:8000/net-000001/a8x72mkq9")


if __name__ == "__main__":
    asyncio.run(seed())
