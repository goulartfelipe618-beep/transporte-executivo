"""Servico de receptivos: modelos de plaquinhas e geracao de PDF."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.branding import brand_display_name

from .reservation_service import find_reservation, reservation_numero_slug

DATA_FILE = Path("data") / "receptivos.json"
PDF_DIR = Path("data") / "receptivos"
LOGO_FILE = Path(__file__).resolve().parents[1] / "static" / "master" / "images" / "favicon.png"

RECEPTION_MODELS = [
    {"id": "classico", "name": "Modelo 1 - Classico com moldura arredondada"},
    {"id": "faixa_superior", "name": "Modelo 2 - Faixa superior e destaque"},
    {"id": "moldura_dupla", "name": "Modelo 3 - Moldura dupla executiva"},
    {"id": "cantos_premium", "name": "Modelo 4 - Cantos premium"},
    {"id": "minimalista", "name": "Modelo 5 - Minimalista corporativo"},
]


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "sim", "yes", "on"}


def _safe_slug(value):
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip()).strip("-")
    return text.lower() or "receptivo"


def _load_items():
    if not DATA_FILE.is_file():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _save_items(items):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def list_receptions():
    return sorted(_load_items(), key=lambda item: item.get("created_at", ""), reverse=True)


def find_reception(reception_id):
    for item in _load_items():
        if str(item.get("id", "")) == str(reception_id or ""):
            return item
    return None


def model_options():
    return list(RECEPTION_MODELS)


def find_model(model_id):
    for model in RECEPTION_MODELS:
        if model["id"] == model_id:
            return model
    return RECEPTION_MODELS[0]


def reservation_options(app):
    options = []
    for reservation in getattr(app, "reservations", []) or []:
        numero = str(reservation.get("numero", "") or "").strip()
        if not numero:
            continue
        options.append(
            {
                "numero": numero,
                "slug": reservation_numero_slug(numero),
                "cliente": reservation.get("cliente", ""),
                "tipo": reservation.get("tipo", ""),
                "data": reservation.get("data", ""),
                "embarque": reservation.get("origem") or _route_part(reservation, 0),
                "desembarque": reservation.get("destino") or _route_part(reservation, 1),
                "label": _reservation_label(reservation),
            }
        )
    return options


def _route_part(reservation, index):
    trajeto = str(reservation.get("trajeto", "") or "")
    for sep in (" -> ", " → ", "->", "→"):
        if sep in trajeto:
            parts = trajeto.split(sep, 1)
            return parts[index].strip() if len(parts) > index else ""
    return trajeto.strip() if index == 0 else ""


def _reservation_label(reservation):
    numero = str(reservation.get("numero", "") or "").strip()
    cliente = str(reservation.get("cliente", "") or "").strip()
    tipo = str(reservation.get("tipo", "") or "").strip()
    data = str(reservation.get("data", "") or "").strip()
    pieces = [numero, cliente]
    suffix = " · ".join(part for part in [tipo, data] if part)
    return " - ".join(part for part in pieces if part) + (f" ({suffix})" if suffix else "")


def _reservation_details(reservation):
    return {
        "numero": str(reservation.get("numero", "") or "").strip(),
        "tipo": str(reservation.get("tipo", "") or "").strip(),
        "embarque": str(reservation.get("origem") or _route_part(reservation, 0) or "").strip(),
        "desembarque": str(reservation.get("destino") or _route_part(reservation, 1) or "").strip(),
        "data": str(reservation.get("data", "") or "").strip(),
    }


def _draw_logo(pdf, width, y):
    if not LOGO_FILE.is_file():
        return
    try:
        image = ImageReader(str(LOGO_FILE))
        size = 94
        pdf.drawImage(image, (width - size) / 2, y, size, size, preserveAspectRatio=True, mask="auto")
    except Exception:
        return


def _draw_model(pdf, model_id, width, height):
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(2)
    if model_id == "faixa_superior":
        pdf.setFillColor(colors.black)
        pdf.rect(0, height - 48, width, 48, fill=1, stroke=0)
        pdf.setStrokeColor(colors.black)
        pdf.line(110, 138, width - 110, 138)
        return
    if model_id == "moldura_dupla":
        pdf.roundRect(18, 18, width - 36, height - 36, 42, stroke=1, fill=0)
        pdf.roundRect(36, 36, width - 72, height - 72, 26, stroke=1, fill=0)
        return
    if model_id == "cantos_premium":
        corner = 92
        pdf.setFillColor(colors.black)
        for x, y, sx, sy in ((0, height, 1, -1), (width, height, -1, -1), (0, 0, 1, 1), (width, 0, -1, 1)):
            path = pdf.beginPath()
            path.moveTo(x, y)
            path.lineTo(x + sx * corner, y)
            path.lineTo(x, y + sy * corner)
            path.close()
            pdf.drawPath(path, fill=1, stroke=0)
        pdf.setStrokeColor(colors.black)
        pdf.line(110, 138, width - 110, 138)
        return
    if model_id == "minimalista":
        pdf.setLineWidth(2)
        pdf.line(90, height - 70, width - 90, height - 70)
        pdf.line(90, 70, width - 90, 70)
        pdf.line(90, 140, width - 90, 140)
        return
    pdf.roundRect(20, 20, width - 40, height - 40, 46, stroke=1, fill=0)
    pdf.line(110, 138, width - 110, 138)


def _draw_details(pdf, details, width, y):
    lines = [
        f"Reserva {details['numero']}  |  Tipo: {details['tipo']}",
        f"Embarque: {details['embarque']}",
        f"Desembarque: {details['desembarque']}",
        f"Data/hora: {details['data']}",
    ]
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 7.5)
    for line in [item for item in lines if item.strip() and not item.endswith(": ")]:
        pdf.drawCentredString(width / 2, y, line[:128])
        y -= 10


def generate_reception_pdf(form_data, reservation):
    model_id = str(form_data.get("model_id") or RECEPTION_MODELS[0]["id"]).strip()
    model = find_model(model_id)
    include_details = _truthy(form_data.get("include_details"))
    client_name = str(form_data.get("client_name") or reservation.get("cliente") or "").strip()
    if not client_name:
        return None, "Informe o nome do cliente."

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    reception_id = f"rec-{uuid.uuid4().hex[:10]}"
    filename = f"{now.strftime('%Y%m%d-%H%M%S')}-{_safe_slug(client_name)}-{_safe_slug(reservation.get('numero'))}.pdf"
    pdf_path = PDF_DIR / filename

    width, height = landscape(A4)
    pdf = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))
    pdf.setTitle(f"Receptivo {client_name}")
    _draw_model(pdf, model["id"], width, height)
    _draw_logo(pdf, width, height - 165)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 42)
    pdf.drawCentredString(width / 2, 215, client_name.upper())

    if include_details:
        _draw_details(pdf, _reservation_details(reservation), width, 120)
    else:
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(width / 2, 116, brand_display_name())

    pdf.showPage()
    pdf.save()

    details = _reservation_details(reservation)
    record = {
        "id": reception_id,
        "created_at": now.isoformat(timespec="seconds"),
        "created_at_label": now.strftime("%d/%m/%Y, %H:%M:%S"),
        "model_id": model["id"],
        "model_name": model["name"],
        "client_name": client_name,
        "reservation_numero": details["numero"],
        "include_details": include_details,
        "embarque": details["embarque"],
        "pdf_filename": filename,
        "pdf_path": str(pdf_path),
    }
    items = _load_items()
    items.insert(0, record)
    _save_items(items[:200])
    return record, ""


def create_reception(app, form_data):
    numero = str(form_data.get("reservation_numero") or "").strip()
    if not numero:
        return None, "Selecione uma reserva Transfer."
    reservation = find_reservation(app, numero)
    if not reservation:
        return None, "Reserva selecionada nao foi encontrada."
    return generate_reception_pdf(form_data, reservation)
