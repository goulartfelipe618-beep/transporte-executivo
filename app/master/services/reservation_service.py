"""CRUD de reservas — logica extraida de reservations.py (sem Tkinter)."""
from __future__ import annotations

import re
import tempfile
from datetime import datetime
from pathlib import Path

from app.portal_auth import active_portal_drivers, find_driver_by_name
from app.reservation_numbers import next_reservation_number, next_reservation_numbers
from app.reservation_pdf import default_pdf_filename, generate_reservation_pdf

from ..services.address_po_service import collect_address_values_from_form
from ..validators.input import (
    calculate_total_amount,
    format_amount,
    parse_amount,
    parse_br_datetime,
    validate_email_value,
    validate_future_datetime,
)

ADDRESS_KEYS = [
    "embarque",
    "desembarque",
    "volta_embarque",
    "volta_desembarque",
    "hora_inicio",
    "hora_fim",
]

EDIT_FIELDS = [
    "cliente",
    "contato",
    "email",
    "tipo",
    "trajeto",
    "data",
    "motorista",
    "valor",
    "status",
]

UNASSIGNED_DRIVER = "-- Nao atribuir ainda --"


def registered_clients(app):
    clients = []
    for client in getattr(app, "clients", []) or []:
        nome = str(client.get("nome") or client.get("razao_social") or client.get("empresa") or "").strip()
        if not nome:
            continue
        clients.append(
            {
                "id": client.get("id", ""),
                "nome": nome,
                "telefone": client.get("telefone", ""),
                "email": client.get("email", ""),
                "documento": client.get("cpf") or client.get("cnpj") or client.get("documento", ""),
            }
        )
    return clients


def registered_drivers(app):
    labels = []
    for driver in active_portal_drivers(app):
        labels.append(f'{driver.get("nome", "")} ({driver.get("id", "")})')
    return labels


def resolve_driver_assignment(app, motorista_label):
    motorista_label = str(motorista_label or "").strip()
    if not motorista_label or motorista_label == UNASSIGNED_DRIVER:
        return "-", ""
    name = motorista_label.split(" (drv-")[0].strip()
    if "(drv-" in motorista_label:
        driver_id = motorista_label.rsplit("(", 1)[1].rstrip(")")
    else:
        driver = find_driver_by_name(app, name)
        driver_id = driver.get("id", "") if driver else ""
    return name or motorista_label, driver_id


def finance_payable_account(reservation_number, motorista):
    clean = str(reservation_number or "").replace("#", "")
    return f"CP-REPASSE-{clean or '0000'}"


def apply_finance_fields(payload, motorista):
    repasse_value = parse_amount(payload.get("repasse"))
    if repasse_value > 0:
        account = finance_payable_account(payload.get("numero"), motorista)
        payload["conta_pagar"] = account
        payload["conta_pagar_descricao"] = f"Repasse motorista — {motorista} — Reserva {payload.get('numero', '')}"
    else:
        payload["conta_pagar"] = ""
        payload["conta_pagar_descricao"] = ""
    return payload


def find_client(clients, name):
    for client in clients:
        if client["nome"] == name:
            return client
    return None


def normalize_numero(numero):
    raw = str(numero or "").strip()
    if raw and not raw.startswith("#"):
        return f"#{raw.lstrip('#')}"
    return raw


def find_reservation(app, numero):
    target = normalize_numero(numero)
    for reservation in getattr(app, "reservations", []) or []:
        if str(reservation.get("numero", "")).strip() == target:
            return reservation
    return None


def _reservation_date_value(reservation):
    value = reservation.get("data", "") if isinstance(reservation, dict) else str(reservation or "")
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    return None


def _parse_filter_date(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 8:
        return None
    try:
        return datetime(int(digits[4:8]), int(digits[2:4]), int(digits[0:2])).date()
    except ValueError:
        return None


def filter_reservations(app, filters=None):
    filters = filters or {}
    items = list(getattr(app, "reservations", []) or [])
    date_from = _parse_filter_date(filters.get("date_from"))
    date_to = _parse_filter_date(filters.get("date_to"))
    estado = str(filters.get("estado", "") or "").strip().upper()
    motorista = str(filters.get("motorista", "") or "").strip().lower()
    search = str(filters.get("search", "") or "").strip().lower()

    if estado and estado not in {"TODOS", "TODOS OS ESTADOS"}:
        filtered = []
        for item in items:
            trajeto = str(item.get("trajeto", "")).upper()
            uf_field = str(item.get("estado_uf", "")).upper()
            if estado in trajeto or estado == uf_field:
                filtered.append(item)
        items = filtered

    if motorista and motorista not in {"todos", "todos os motoristas"}:
        items = [item for item in items if motorista in str(item.get("motorista", "")).lower()]

    if date_from or date_to:
        filtered = []
        for item in items:
            reservation_date = _reservation_date_value(item)
            if not reservation_date:
                continue
            if date_from and reservation_date < date_from:
                continue
            if date_to and reservation_date > date_to:
                continue
            filtered.append(item)
        items = filtered

    if search:
        filtered = []
        for item in items:
            haystack = " ".join(
                [
                    str(item.get("numero", "")),
                    str(item.get("cliente", "")),
                    str(item.get("contato", "")),
                    str(item.get("email", "")),
                ]
            ).lower()
            if search in haystack:
                filtered.append(item)
        items = filtered

    return items


def _reservation_location_meta(values, embarque_key, desembarque_key=None):
    meta = {
        f"{embarque_key}_po_id": values.get(f"{embarque_key}_po_id", ""),
        f"{embarque_key}_modo": values.get(f"{embarque_key}_modo", "manual"),
    }
    if desembarque_key:
        meta[f"{desembarque_key}_po_id"] = values.get(f"{desembarque_key}_po_id", "")
        meta[f"{desembarque_key}_modo"] = values.get(f"{desembarque_key}_modo", "manual")
    return meta


def _validate_create_payload(values):
    required = {
        "nome": "Nome Completo",
        "documento": "CPF/CNPJ",
        "email": "Email",
        "telefone": "Telefone",
        "valor_base": "Valor Base",
    }
    trip_type = values.get("tipo", "Somente Ida")
    if trip_type == "Por Hora":
        required.update(
            {
                "hora_inicio": "Endereco de Inicio",
                "hora_fim": "Ponto de Encerramento",
                "hora_data": "Data",
                "hora_horario": "Hora de inicio",
                "hora_passageiros": "Passageiros",
                "qtd_horas": "Qtd. Horas",
            }
        )
    else:
        required.update(
            {
                "embarque": "Local de Embarque",
                "desembarque": "Local de Desembarque",
                "data": "Data do Embarque",
                "hora": "Hora do Embarque",
                "passageiros": "Passageiros",
            }
        )
        if trip_type == "Ida e Volta":
            required.update(
                {
                    "volta_embarque": "Local de Embarque (Volta)",
                    "volta_desembarque": "Local de Desembarque (Volta)",
                    "volta_data": "Data da Volta",
                    "volta_hora": "Hora da Volta",
                }
            )

    for key, label in required.items():
        if not str(values.get(key, "") or "").strip():
            return False, f"Informe: {label}."

    ok, msg = validate_email_value(values.get("email"), label="Email")
    if not ok:
        return False, msg

    documento = re.sub(r"\D", "", str(values.get("documento", "")))
    if len(documento) not in {11, 14}:
        return False, "Informe um CPF (11 digitos) ou CNPJ (14 digitos) valido."

    telefone = re.sub(r"\D", "", str(values.get("telefone", "")))
    if len(telefone) < 10:
        return False, "Informe um telefone completo no formato (XX) X XXXX-XXXX."

    if trip_type == "Por Hora":
        ok, msg = validate_future_datetime(values.get("hora_data"), values.get("hora_horario"), label="Data/hora do servico")
        if not ok:
            return False, msg
    else:
        ok, msg = validate_future_datetime(values.get("data"), values.get("hora"), label="Data/hora de embarque (IDA)")
        if not ok:
            return False, msg
        if trip_type == "Ida e Volta":
            ok, msg = validate_future_datetime(values.get("volta_data"), values.get("volta_hora"), label="Data/hora de embarque (VOLTA)")
            if not ok:
                return False, msg
            ida_dt = parse_br_datetime(values.get("data"), values.get("hora"))
            volta_dt = parse_br_datetime(values.get("volta_data"), values.get("volta_hora"))
            if ida_dt and volta_dt and volta_dt < ida_dt:
                return False, "A volta nao pode ser anterior a ida."

    return True, ""


def create_reservation(app, form_data):
    values = {key: str(form_data.get(key, "") or "").strip() for key in form_data.keys()}
    values.update(collect_address_values_from_form(app, form_data, ADDRESS_KEYS))

    client_mode = str(form_data.get("client_mode", "novo") or "novo").strip().lower()
    if client_mode == "cadastrado":
        clients = registered_clients(app)
        selected = str(form_data.get("cliente_cadastrado", "") or "").strip()
        client = find_client(clients, selected)
        if client:
            values["nome"] = client["nome"]
            values["telefone"] = client["telefone"]
            values["email"] = client["email"]
            values["documento"] = client["documento"]

    ok, error = _validate_create_payload(values)
    if not ok:
        return None, error, []

    total_value = calculate_total_amount(values.get("valor_base"), values.get("desconto"))
    valor = format_amount(total_value)
    repasse_total = parse_amount(values.get("repasse"))
    motorista, driver_id = resolve_driver_assignment(app, values.get("motorista"))

    common = {
        "cliente": values["nome"],
        "contato": values["telefone"],
        "email": values["email"],
        "motorista": motorista,
        "driver_id": driver_id,
        "valor": valor,
        "valor_base": values.get("valor_base", ""),
        "desconto": values.get("desconto", "0"),
        "status": values.get("status") or "Pendente",
        "documento": values["documento"],
        "pagamento": values.get("pagamento", ""),
        "repasse": values.get("repasse", "0,00"),
    }

    created = []
    trip_type = values.get("tipo", "Somente Ida")
    repasse_ida = repasse_total
    repasse_volta = 0.0
    if trip_type == "Ida e Volta" and repasse_total > 0:
        repasse_ida = round(repasse_total / 2, 2)
        repasse_volta = round(repasse_total - repasse_ida, 2)

    if trip_type == "Ida e Volta":
        pair_id = f"pair-{len(app.reservations) + 1:04d}"
        ida_num, volta_num = next_reservation_numbers(app, 2)
        ida_data = values["data"]
        if values.get("hora"):
            ida_data = f"{ida_data} {values['hora']}"
        volta_data = values["volta_data"]
        if values.get("volta_hora"):
            volta_data = f"{volta_data} {values['volta_hora']}"

        ida_res = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "embarque", "desembarque"),
                "numero": ida_num,
                "tipo": "Ida",
                "trajeto": f'{values["embarque"]} -> {values["desembarque"]}',
                "data": ida_data,
                "hora": values.get("hora", ""),
                "passageiros": values["passageiros"],
                "repasse": format_amount(repasse_ida) if repasse_ida > 0 else "0,00",
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("mensagem", "")])).strip(),
                "par_id": pair_id,
                "perna": "ida",
            },
            motorista,
        )
        volta_res = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "volta_embarque", "volta_desembarque"),
                "numero": volta_num,
                "tipo": "Volta",
                "trajeto": f'{values["volta_embarque"]} -> {values["volta_desembarque"]}',
                "data": volta_data,
                "hora": values.get("volta_hora", ""),
                "passageiros": values.get("volta_passageiros") or values["passageiros"],
                "repasse": format_amount(repasse_volta) if repasse_volta > 0 else "0,00",
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("volta_mensagem", "")])).strip(),
                "par_id": pair_id,
                "perna": "volta",
            },
            motorista,
        )
        app.reservations.insert(0, volta_res)
        app.reservations.insert(0, ida_res)
        created.extend([ida_res, volta_res])
    elif trip_type == "Por Hora":
        reservation = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "hora_inicio", "hora_fim"),
                "numero": next_reservation_number(app),
                "tipo": values["tipo"],
                "trajeto": f'{values["hora_inicio"]} -> {values["hora_fim"]}',
                "data": values["hora_data"],
                "hora": values.get("hora_horario", ""),
                "passageiros": values["hora_passageiros"],
                "observacoes": values.get("hora_observacoes", ""),
            },
            motorista,
        )
        app.reservations.insert(0, reservation)
        created.append(reservation)
    else:
        data = values["data"]
        hora = values.get("hora", "")
        if hora:
            data = f"{data} {hora}"
        reservation = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "embarque", "desembarque"),
                "numero": next_reservation_number(app),
                "tipo": values["tipo"],
                "trajeto": f'{values["embarque"]} -> {values["desembarque"]}',
                "data": data,
                "hora": hora,
                "passageiros": values["passageiros"],
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("mensagem", "")])).strip(),
            },
            motorista,
        )
        app.reservations.insert(0, reservation)
        created.append(reservation)

    app.save_state()
    return created, "", payable_notices(created)


def update_reservation(app, numero, form_data):
    reservation = find_reservation(app, numero)
    if not reservation:
        return False, "Reserva nao encontrada."

    values = {key: str(form_data.get(key, reservation.get(key, "")) or "").strip() for key in EDIT_FIELDS}
    if not values.get("cliente"):
        return False, "Informe o cliente da reserva."

    ok, msg = validate_email_value(values.get("email"), label="E-mail")
    if not ok:
        return False, msg

    reservation.update(values)
    app.save_state()
    return True, ""


def delete_reservation(app, numero):
    reservation = find_reservation(app, numero)
    if not reservation:
        return False, "Reserva nao encontrada."
    app.reservations.remove(reservation)
    app.save_state()
    return True, ""


def payable_notices(created):
    return [
        f'{item["conta_pagar"]}: {item["conta_pagar_descricao"]} ({item.get("repasse", "")})'
        for item in created or []
        if parse_amount(item.get("repasse")) > 0
    ]


def pdf_filename(reservation, via):
    return default_pdf_filename(reservation, via)


def generate_pdf_bytes(reservation, app, via):
    via = str(via or "loja").lower()
    if via not in {"cliente", "motorista", "loja"}:
        via = "loja"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = tmp.name
    try:
        generate_reservation_pdf(reservation, app, via, path)
        return Path(path).read_bytes()
    finally:
        Path(path).unlink(missing_ok=True)
