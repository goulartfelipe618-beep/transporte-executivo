"""Links de rastreamento em tempo real (Geolocalizador)."""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime

TRACKING_LINKS_FILE = os.path.join("data", "tracking_links.json")
TOKEN_BYTES = 18

TARGET_CLIENTE = "cliente"
TARGET_MOTORISTA = "motorista"
TARGET_LABELS = {
    TARGET_CLIENTE: "Cliente",
    TARGET_MOTORISTA: "Motorista",
}

STATUS_WAITING = "aguardando"
STATUS_ACTIVE = "ativa"
STATUS_ENDED = "encerrada"

STATUS_LABELS = {
    STATUS_WAITING: "Aguardando iniciar",
    STATUS_ACTIVE: "Viagem ativa",
    STATUS_ENDED: "Encerrada",
}


def _next_link_id(items):
    numbers = []
    for item in items or []:
        raw = str(item.get("id", ""))
        if raw.startswith("trk-"):
            try:
                numbers.append(int(raw.split("-", 1)[1]))
            except ValueError:
                pass
    return f"trk-{(max(numbers) + 1) if numbers else 1:04d}"


def normalize_tracking_link(item):
    if not item or not item.get("token"):
        return None
    target = str(item.get("target_type", "")).strip().lower()
    if target not in TARGET_LABELS:
        return None
    status = str(item.get("status", STATUS_WAITING)).strip().lower()
    if status not in STATUS_LABELS:
        status = STATUS_WAITING
    return {
        "id": str(item.get("id") or _next_link_id([])),
        "token": str(item.get("token")),
        "reservation_id": str(item.get("reservation_id", "")),
        "reservation_numero": str(item.get("reservation_numero", "")),
        "target_type": target,
        "cliente_nome": str(item.get("cliente_nome", "")).strip(),
        "telefone": str(item.get("telefone", "")).strip(),
        "observacoes": str(item.get("observacoes", "")).strip(),
        "status": status,
        "created_at": str(item.get("created_at") or datetime.now().isoformat(timespec="seconds")),
        "created_by": str(item.get("created_by", "")).strip(),
        "communicated_at": str(item.get("communicated_at", "")).strip(),
        "started_at": str(item.get("started_at", "")).strip(),
        "ended_at": str(item.get("ended_at", "")).strip(),
        "positions": list(item.get("positions") or [])[-500:],
        "last_position": dict(item.get("last_position") or {}),
        "summary": dict(item.get("summary") or {}),
    }


def tracking_public_path(token):
    return f"/rastreio/{token}"


def tracking_public_url(token, base_url=""):
    from app.portal_urls import tracking_portal_base

    base = str(base_url or tracking_portal_base()).rstrip("/")
    path = tracking_public_path(token)
    return f"{base}{path}" if base else path


def ensure_tracking_links_loaded(app):
    if getattr(app, "tracking_links", None) is not None:
        app.tracking_links = [
            row for row in (normalize_tracking_link(item) for item in app.tracking_links) if row
        ]
        return
    items = []
    if os.path.exists(TRACKING_LINKS_FILE):
        try:
            with open(TRACKING_LINKS_FILE, encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, list):
                items = raw
        except (json.JSONDecodeError, OSError):
            items = []
    app.tracking_links = [row for row in (normalize_tracking_link(item) for item in items) if row]


def save_tracking_links(app):
    ensure_tracking_links_loaded(app)
    valid = [normalize_tracking_link(item) for item in app.tracking_links if normalize_tracking_link(item)]
    app.tracking_links = valid
    os.makedirs(os.path.dirname(TRACKING_LINKS_FILE), exist_ok=True)
    with open(TRACKING_LINKS_FILE, "w", encoding="utf-8") as handle:
        json.dump(valid, handle, ensure_ascii=False, indent=2)


def new_tracking_token():
    return secrets.token_urlsafe(TOKEN_BYTES)
