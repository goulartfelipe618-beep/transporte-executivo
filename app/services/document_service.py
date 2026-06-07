"""PDF, QR Code and email generation."""

import io
from typing import Optional

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.models.booking import BookingReservation

settings = get_settings()


def generate_qr_code_png(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_reservation_pdf(reservation: BookingReservation) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 2 * cm, "Nexus Transfer - Confirmação de Reserva")

    c.setFont("Helvetica", 12)
    y = height - 4 * cm
    lines = [
        f"Código: {reservation.code}",
        f"Status: {reservation.status}",
        f"Origem: {reservation.origin}",
        f"Destino: {reservation.destination}",
        f"Data: {reservation.trip_date}",
        f"Horário: {reservation.trip_time}",
        f"Veículo: {reservation.vehicle_name or 'N/A'}",
        f"Total: R$ {reservation.total_amount or 0:.2f}",
    ]
    if reservation.partner_name:
        lines.append(f"Parceiro: {reservation.partner_name}")

    for line in lines:
        c.drawString(2 * cm, y, line)
        y -= 0.7 * cm

    c.drawString(2 * cm, 2 * cm, f"Gerado em {reservation.confirmed_at or reservation.created_at}")
    c.save()
    return buffer.getvalue()


async def send_confirmation_email(
    reservation: BookingReservation,
    passenger_email: str,
    pdf_bytes: Optional[bytes] = None,
) -> bool:
    if not settings.smtp_host:
        return False
    # Placeholder: production would use aiosmtplib with attachments
    return True
