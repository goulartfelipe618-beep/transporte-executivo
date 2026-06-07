"""Booking flow web pages."""

from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import booking_service
from app.services.document_service import generate_qr_code_png, generate_reservation_pdf
from app.services.partner_service import get_partner_by_external_id

router = APIRouter(prefix="/booking", tags=["booking-web"])
templates = Jinja2Templates(directory="app/templates")


async def _partner_context(request: Request, db: AsyncSession):
    partner = None
    ext_id = request.session.get("partner_external_id")
    if ext_id:
        partner = await get_partner_by_external_id(db, ext_id)
    return partner


@router.get("/{reservation_id}/vehicles", response_class=HTMLResponse)
async def vehicles_page(
    reservation_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(404)
    vehicles = await booking_service.get_available_vehicles(
        reservation.origin, reservation.destination, reservation.passengers, reservation.luggage
    )
    partner = await _partner_context(request, db)
    return templates.TemplateResponse(
        request,
        "booking/vehicles.html",
        {
            "reservation": reservation,
            "vehicles": vehicles,
            "partner": partner,
            "step": 2,
            "vehicle_count": len(vehicles),
        },
    )


@router.get("/{reservation_id}/passenger", response_class=HTMLResponse)
async def passenger_page(reservation_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(404)
    partner = await _partner_context(request, db)
    return templates.TemplateResponse(
        request,
        "booking/passenger.html",
        {"reservation": reservation, "partner": partner, "step": 3, "csrf_token": request.session.get("csrf_token")},
    )


@router.get("/{reservation_id}/summary", response_class=HTMLResponse)
async def summary_page(reservation_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(404)
    partner = await _partner_context(request, db)
    return templates.TemplateResponse(
        request,
        "booking/summary.html",
        {"reservation": reservation, "partner": partner, "step": 4},
    )


@router.get("/{reservation_id}/payment", response_class=HTMLResponse)
async def payment_page(reservation_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(404)
    partner = await _partner_context(request, db)
    return templates.TemplateResponse(
        request,
        "booking/payment.html",
        {"reservation": reservation, "partner": partner, "step": 5},
    )


@router.get("/{reservation_id}/confirmation", response_class=HTMLResponse)
async def confirmation_page(reservation_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation or reservation.status != "confirmed":
        raise HTTPException(404)
    partner = await _partner_context(request, db)
    return templates.TemplateResponse(
        request,
        "booking/confirmation.html",
        {"reservation": reservation, "partner": partner, "step": 6},
    )


@router.get("/{reservation_id}/qr")
async def qr_code(reservation_id: UUID, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(404)
    data = reservation.qr_code_data or f"NEXUS:{reservation.code}"
    return Response(content=generate_qr_code_png(data), media_type="image/png")


@router.get("/{reservation_id}/pdf")
async def pdf_download(reservation_id: UUID, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(404)
    pdf = generate_reservation_pdf(reservation)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="reserva-{reservation.code}.pdf"'},
    )
