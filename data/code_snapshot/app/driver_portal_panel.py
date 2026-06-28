"""Mini painel do motorista: clientes, reservas proprias, PDF e seguranca."""
from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime

from .company_model import is_corporate_client, next_company_id
from .portal_auth import log_portal_event
from .repository.ids import next_entity_id
from .reservation_numbers import next_reservation_number
from .reservation_pdf import default_pdf_filename, generate_reservation_pdf
from .totp_auth import generate_totp_secret, provisioning_uri, totp_qr_data_url, verify_totp_code


DRIVER_OWNER_TYPE = "motorista"
DRIVER_SOURCE = "portal_motorista"


def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _clean(value) -> str:
    return str(value or "").strip()


def _bool(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "sim", "on", "ativo"}


def driver_display_name(driver) -> str:
    return _clean(driver.get("nome")) or _clean(driver.get("id")) or "Motorista"


def driver_panel_config(driver) -> dict:
    config = dict(driver.get("portal_panel") or {})
    config.setdefault("business_name", driver_display_name(driver))
    config.setdefault("logo_url", _clean(driver.get("logo_url") or driver.get("foto_perfil")))
    config.setdefault("contract_text", "")
    config.setdefault("primary_color", "#3b82f6")
    config.setdefault("totp_enabled", False)
    config.setdefault("totp_secret", "")
    config.setdefault("totp_pending_secret", "")
    return config


def public_panel_config(driver) -> dict:
    config = driver_panel_config(driver)
    return {
        "business_name": config.get("business_name", ""),
        "logo_url": config.get("logo_url", ""),
        "contract_text": config.get("contract_text", ""),
        "primary_color": config.get("primary_color", "#3b82f6"),
        "totp_enabled": bool(config.get("totp_enabled") and config.get("totp_secret")),
    }


def save_panel_config(driver, payload) -> dict:
    config = driver_panel_config(driver)
    for key in ("business_name", "logo_url", "contract_text", "primary_color"):
        if key in payload:
            config[key] = _clean(payload.get(key))
    if not config.get("business_name"):
        config["business_name"] = driver_display_name(driver)
    driver["portal_panel"] = config
    return public_panel_config(driver)


def begin_totp_setup(driver) -> dict:
    config = driver_panel_config(driver)
    secret = generate_totp_secret()
    config["totp_pending_secret"] = secret
    driver["portal_panel"] = config
    account = _clean(driver.get("email")) or _clean(driver.get("cpf")) or driver_display_name(driver)
    uri = provisioning_uri(secret, account, issuer="Portal Motorista")
    return {"secret": secret, "qr": totp_qr_data_url(uri)}


def enable_driver_totp(driver, code: str) -> tuple[bool, str]:
    config = driver_panel_config(driver)
    secret = _clean(config.get("totp_pending_secret"))
    if not secret:
        return False, "Inicie a configuracao do 2FA antes de confirmar."
    if not verify_totp_code(secret, code):
        return False, "Codigo 2FA invalido."
    config["totp_secret"] = secret
    config["totp_enabled"] = True
    config["totp_pending_secret"] = ""
    config["totp_enabled_at"] = _now()
    driver["portal_panel"] = config
    return True, ""


def disable_driver_totp(driver, code: str) -> tuple[bool, str]:
    ok, message = verify_driver_totp(driver, code)
    if not ok:
        return False, message
    config = driver_panel_config(driver)
    config["totp_secret"] = ""
    config["totp_enabled"] = False
    config["totp_pending_secret"] = ""
    config["totp_enabled_at"] = ""
    driver["portal_panel"] = config
    return True, ""


def verify_driver_totp(driver, code: str) -> tuple[bool, str]:
    config = driver_panel_config(driver)
    if not config.get("totp_enabled") or not config.get("totp_secret"):
        return True, ""
    if verify_totp_code(config.get("totp_secret", ""), code):
        return True, ""
    return False, "Codigo 2FA invalido."


def _driver_identity(driver) -> set[str]:
    return {str(driver.get(key, "")).strip() for key in ("id", "uuid", "supabase_id") if str(driver.get(key, "")).strip()}


def is_driver_owned_reservation(reservation, driver) -> bool:
    ids = _driver_identity(driver)
    return str(reservation.get("owner_type", "")).strip() == DRIVER_OWNER_TYPE and str(reservation.get("created_by_driver_id", "")).strip() in ids


def is_driver_visible_reservation(reservation, driver) -> bool:
    ids = _driver_identity(driver)
    assigned = {str(reservation.get(key, "")).strip() for key in ("driver_id", "driver_uuid") if str(reservation.get(key, "")).strip()}
    return bool(assigned & ids) or is_driver_owned_reservation(reservation, driver)


def list_driver_clients(app, driver) -> list[dict]:
    driver_id = str(driver.get("id", ""))
    items = []
    for client in getattr(app, "clients", []) or []:
        if str(client.get("created_by_driver_id", "")) != driver_id:
            continue
        items.append(client_dto(client))
    items.sort(key=lambda row: row.get("nome", "").lower())
    return items


def client_dto(client) -> dict:
    corporate = is_corporate_client(client)
    return {
        "id": client.get("id", ""),
        "tipo_pessoa": "juridica" if corporate else "fisica",
        "nome": client.get("nome_fantasia") or client.get("razao_social") or client.get("nome") or client.get("nome_completo") or "",
        "documento": client.get("cnpj") if corporate else (client.get("cpf") or client.get("documento") or client.get("cpf_cnpj") or ""),
        "email": client.get("email", ""),
        "telefone": client.get("telefone", ""),
    }


def find_driver_client(app, driver, client_id):
    driver_id = str(driver.get("id", ""))
    for client in getattr(app, "clients", []) or []:
        if str(client.get("id", "")) == str(client_id) and str(client.get("created_by_driver_id", "")) == driver_id:
            return client
    return None


def create_driver_client(app, driver, payload) -> dict:
    tipo = _clean(payload.get("tipo_pessoa")).lower()
    clients = list(getattr(app, "clients", []) or [])
    if tipo in {"juridica", "empresa", "pj"}:
        client = {
            "id": next_company_id(clients),
            "tipo_pessoa": "juridica",
            "razao_social": _clean(payload.get("razao_social") or payload.get("nome")),
            "nome_fantasia": _clean(payload.get("nome_fantasia") or payload.get("nome")),
            "cnpj": _clean(payload.get("documento") or payload.get("cnpj")),
            "email": _clean(payload.get("email")).lower(),
            "telefone": _clean(payload.get("telefone")),
            "responsavel": _clean(payload.get("responsavel")),
            "portal_ativo": False,
            "status_empresa": "Ativa",
        }
        client["nome"] = client["nome_fantasia"] or client["razao_social"]
    else:
        client = {
            "id": next_entity_id("cli", clients),
            "tipo_pessoa": "fisica",
            "nome": _clean(payload.get("nome")),
            "nome_completo": _clean(payload.get("nome")),
            "documento": _clean(payload.get("documento") or payload.get("cpf")),
            "cpf": _clean(payload.get("documento") or payload.get("cpf")),
            "cpf_cnpj": _clean(payload.get("documento") or payload.get("cpf")),
            "email": _clean(payload.get("email")).lower(),
            "telefone": _clean(payload.get("telefone")),
        }
    client["created_by_driver_id"] = driver.get("id", "")
    client["created_by_driver_name"] = driver_display_name(driver)
    client["source"] = DRIVER_SOURCE
    client["criado_em"] = _now()
    clients.append(client)
    app.clients = clients
    if hasattr(app, "save_state"):
        app.save_state()
    return client


def _resolve_client_for_reservation(app, driver, payload):
    client = find_driver_client(app, driver, payload.get("client_id"))
    if client:
        dto = client_dto(client)
        return dto["nome"], dto["documento"], dto["email"], dto["telefone"], dto["id"], dto["tipo_pessoa"]
    return (
        _clean(payload.get("cliente") or payload.get("nome")),
        _clean(payload.get("documento")),
        _clean(payload.get("email")).lower(),
        _clean(payload.get("telefone")),
        "",
        _clean(payload.get("tipo_cliente")) or "fisica",
    )


def create_driver_reservation(app, driver, payload) -> dict:
    cliente, documento, email, telefone, client_id, client_kind = _resolve_client_for_reservation(app, driver, payload)
    origem = _clean(payload.get("origem"))
    destino = _clean(payload.get("destino"))
    if not cliente or not origem or not destino or not _clean(payload.get("data")):
        raise ValueError("Informe cliente, origem, destino e data.")
    reservation = {
        "id": next_entity_id("res", getattr(app, "reservations", []) or []),
        "numero": next_reservation_number(app),
        "tipo": _clean(payload.get("tipo")) or "Somente Ida",
        "cliente": cliente,
        "documento": documento,
        "contato": telefone,
        "email": email,
        "trajeto": f"{origem} -> {destino}",
        "origem": origem,
        "destino": destino,
        "data": _clean(payload.get("data")),
        "hora": _clean(payload.get("hora")),
        "passageiros": _clean(payload.get("passageiros")) or "1",
        "observacoes": _clean(payload.get("observacoes")),
        "valor": _clean(payload.get("valor")) or "R$ 0,00",
        "pagamento": _clean(payload.get("pagamento")),
        "status": _clean(payload.get("status")) or "Confirmada",
        "motorista": driver_display_name(driver),
        "driver_id": driver.get("id", ""),
        "created_by_driver_id": driver.get("id", ""),
        "created_by_driver_name": driver_display_name(driver),
        "owner_type": DRIVER_OWNER_TYPE,
        "source": DRIVER_SOURCE,
        "flow": "driver_self_service",
        "canal_origem": "portal_motorista",
        "client_id": client_id,
        "client_kind": client_kind,
        "criado_em": _now(),
    }
    app.reservations = [reservation] + list(getattr(app, "reservations", []) or [])
    log_portal_event(
        app,
        "portal.driver.reservation_created",
        f"Reserva {reservation['numero']} criada pelo motorista",
        user_type="driver",
        user_id=driver.get("id", ""),
        referencia_id=reservation["numero"],
    )
    if hasattr(app, "save_state"):
        app.save_state()
    return reservation


def update_driver_reservation(app, driver, numero, payload) -> tuple[bool, str]:
    reservation = find_driver_reservation(app, driver, numero)
    if not reservation:
        return False, "Reserva nao encontrada."
    if not is_driver_owned_reservation(reservation, driver):
        return False, "Somente reservas criadas pelo motorista podem ser editadas."
    if str(reservation.get("status", "")).lower() in {"concluida", "concluído", "concluido", "cancelada", "cancelado"}:
        return False, "Reserva finalizada nao pode ser editada."
    for key in ("data", "hora", "passageiros", "observacoes", "valor", "pagamento"):
        if key in payload:
            reservation[key] = _clean(payload.get(key))
    if "origem" in payload or "destino" in payload:
        origem = _clean(payload.get("origem")) or reservation.get("origem") or reservation.get("trajeto", "").split("->", 1)[0].strip()
        destino = _clean(payload.get("destino")) or reservation.get("destino") or (reservation.get("trajeto", "").split("->", 1)[1].strip() if "->" in reservation.get("trajeto", "") else "")
        reservation["origem"] = origem
        reservation["destino"] = destino
        reservation["trajeto"] = f"{origem} -> {destino}"
    reservation["atualizado_em"] = _now()
    if hasattr(app, "save_state"):
        app.save_state()
    return True, ""


def cancel_driver_reservation(app, driver, numero) -> tuple[bool, str]:
    reservation = find_driver_reservation(app, driver, numero)
    if not reservation:
        return False, "Reserva nao encontrada."
    if not is_driver_owned_reservation(reservation, driver):
        return False, "Somente reservas criadas pelo motorista podem ser canceladas diretamente."
    reservation["status"] = "Cancelada"
    reservation["atualizado_em"] = _now()
    if hasattr(app, "save_state"):
        app.save_state()
    return True, ""


def find_driver_reservation(app, driver, numero):
    target = str(numero or "").strip()
    for reservation in getattr(app, "reservations", []) or []:
        if str(reservation.get("numero", "")) == target and is_driver_visible_reservation(reservation, driver):
            return reservation
    return None


def pdf_for_driver_reservation(app, driver, numero, via="cliente") -> tuple[bytes, str]:
    reservation = find_driver_reservation(app, driver, numero)
    if not reservation:
        raise ValueError("Reserva nao encontrada.")
    config = driver_panel_config(driver)
    pdf_reservation = dict(reservation)
    pdf_reservation["pdf_company_name"] = config.get("business_name") or driver_display_name(driver)
    pdf_reservation["pdf_logo_path"] = config.get("logo_url", "")
    pdf_reservation["driver_contract_text"] = config.get("contract_text", "")
    via = str(via or "cliente").lower()
    if via not in {"cliente", "motorista", "loja"}:
        via = "cliente"
    filename = default_pdf_filename(pdf_reservation, via)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, filename)
        generate_reservation_pdf(pdf_reservation, app, via, path)
        with open(path, "rb") as handle:
            return handle.read(), filename


def pdf_payload(app, driver, numero, via="cliente") -> dict:
    content, filename = pdf_for_driver_reservation(app, driver, numero, via)
    return {
        "filename": filename,
        "content_base64": base64.b64encode(content).decode("ascii"),
        "mime": "application/pdf",
    }
