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
    "valor_base",
    "desconto",
    "pagamento",
    "repasse",
    "status",
]

UNASSIGNED_DRIVER = "-- Nao atribuir ainda --"

_TRIP_TYPE_LABELS = {
    "one_way": "Somente Ida",
    "round_trip": "Ida e Volta",
    "hourly": "Por Hora",
    "ida": "Ida",
    "volta": "Volta",
}

_PRESERVED_RESERVATION_KEYS = (
    "id",
    "uuid",
    "numero",
    "par_id",
    "perna",
    "source",
    "flow",
    "partner_id",
    "partner_slug",
    "partner_code",
    "contributor_id",
    "contributor_code",
    "canal_origem",
    "via_qr",
    "transport_request_legacy_id",
    "draft_id",
    "quote_id",
    "vehicle_name",
    "company_id",
    "cost_center_id",
)


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


def _route_fields(embarque, desembarque):
    origem = str(embarque or "").strip()
    destino = str(desembarque or "").strip()
    return {
        "trajeto": f"{origem} -> {destino}",
        "origem": origem,
        "destino": destino,
    }


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "sim", "on", "faturado"}


def _billing_flags(form_data) -> dict:
    faturado_raw = form_data.get("faturado", "")
    return {
        "faturado": _truthy(faturado_raw),
        "esconder_valores": _truthy(form_data.get("esconder_valores", "")),
    }


def find_client(clients, name):
    for client in clients:
        if client["nome"] == name:
            return client
    return None


def normalize_numero(numero):
    raw = str(numero or "").strip()
    if not raw:
        return raw
    plain = raw.lstrip("#")
    if plain.isdigit():
        return f"#{plain}"
    return plain


def reservation_numero_slug(numero):
    return str(numero or "").strip().lstrip("#")


def find_reservation(app, numero):
    query = reservation_numero_slug(numero)
    if not query:
        return None
    for reservation in getattr(app, "reservations", []) or []:
        stored = reservation_numero_slug(reservation.get("numero", ""))
        if stored and stored.upper() == query.upper():
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


def _split_data_hora(value, fallback_hora=""):
    raw = str(value or "").strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")
        except ValueError:
            pass
    return raw, str(fallback_hora or "").strip()


def _parse_trajeto_endpoints(trajeto, reservation=None):
    text = str(trajeto or "")
    for sep in (" -> ", " → ", "→", "->"):
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    if reservation:
        origem = str(reservation.get("origem", "") or "").strip()
        destino = str(reservation.get("destino", "") or "").strip()
        if origem or destino:
            return origem, destino
    return text.strip(), ""


def _normalize_trip_type(tipo):
    raw = str(tipo or "").strip()
    if raw in {"Somente Ida", "Ida e Volta", "Por Hora", "Ida", "Volta"}:
        return raw
    return _TRIP_TYPE_LABELS.get(raw.lower(), "Somente Ida")


def _normalize_reservation_datetime(value, hora=""):
    raw = str(value or "").strip()
    hora_value = str(hora or "").strip()
    if not raw:
        return "", hora_value
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        try:
            dt = datetime.strptime(raw[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y"), hora_value
        except ValueError:
            pass
    return _split_data_hora(raw, hora_value)


def _find_pair_sibling(app, reservation):
    par_id = reservation.get("par_id")
    if not par_id:
        return None
    numero = reservation.get("numero")
    for item in getattr(app, "reservations", []) or []:
        if item.get("par_id") == par_id and item.get("numero") != numero:
            return item
    return None


def _match_client_mode(app, reservation):
    cadastro_id = str(reservation.get("cliente_cadastro_id", "") or "").strip()
    cadastro_tipo = str(reservation.get("cliente_cadastro_tipo", "") or "").strip()
    if cadastro_id and cadastro_tipo:
        prefix = "emp" if cadastro_tipo == "empresa" else "cli"
        return "cadastrado", f"{prefix}:{cadastro_id}"
    from .client_service import booking_customer_options

    nome = str(reservation.get("cliente", "")).strip().lower()
    for opt in booking_customer_options(app):
        if str(opt.get("nome", "")).strip().lower() == nome:
            return "cadastrado", opt["value"]
    return "novo", ""


def _motorista_label_from_reservation(reservation):
    motorista = str(reservation.get("motorista", "") or "").strip()
    driver_id = str(reservation.get("driver_id", "") or "").strip()
    if motorista.lower() in {"", "-", "none", "null"}:
        return UNASSIGNED_DRIVER
    if driver_id and f"({driver_id})" not in motorista:
        return f"{motorista} ({driver_id})"
    return motorista


def _apply_po_fields_to_form(form, reservation, embarque_key, desembarque_key=None):
    form[f"{embarque_key}_modo"] = reservation.get(f"{embarque_key}_modo", "manual")
    form[f"{embarque_key}_po_id"] = reservation.get(f"{embarque_key}_po_id", "")
    if desembarque_key:
        form[f"{desembarque_key}_modo"] = reservation.get(f"{desembarque_key}_modo", "manual")
        form[f"{desembarque_key}_po_id"] = reservation.get(f"{desembarque_key}_po_id", "")


def _apply_reservation_client_to_form(app, form, reservation):
    client_mode, cliente_cadastrado = _match_client_mode(app, reservation)
    form["client_mode"] = client_mode
    form["cliente_cadastrado"] = cliente_cadastrado
    form["nome"] = reservation.get("cliente", "")
    form["telefone"] = reservation.get("contato", "")
    form["email"] = reservation.get("email", "")
    form["documento"] = reservation.get("documento", "")


def reservation_to_form_dict(app, reservation):
    """Converte reserva persistida para o mesmo formato do formulario de criacao."""
    form = {}
    _apply_reservation_client_to_form(app, form, reservation)

    sibling = _find_pair_sibling(app, reservation)
    perna = reservation.get("perna")
    stored_tipo = str(reservation.get("tipo", "") or "").strip()

    if sibling and perna in {"ida", "volta"}:
        ida_res = reservation if perna == "ida" else sibling
        volta_res = sibling if perna == "ida" else reservation
        form["tipo"] = "Ida e Volta"
        form["embarque"], form["desembarque"] = _parse_trajeto_endpoints(ida_res.get("trajeto"), ida_res)
        form["data"], form["hora"] = _normalize_reservation_datetime(ida_res.get("data"), ida_res.get("hora"))
        form["passageiros"] = ida_res.get("passageiros") or "1"
        _apply_po_fields_to_form(form, ida_res, "embarque", "desembarque")
        form["volta_embarque"], form["volta_desembarque"] = _parse_trajeto_endpoints(volta_res.get("trajeto"), volta_res)
        form["volta_data"], form["volta_hora"] = _split_data_hora(volta_res.get("data"), volta_res.get("hora"))
        form["volta_passageiros"] = volta_res.get("passageiros", "")
        _apply_po_fields_to_form(form, volta_res, "volta_embarque", "volta_desembarque")
        repasse_total = parse_amount(ida_res.get("repasse")) + parse_amount(volta_res.get("repasse"))
        form["repasse"] = format_amount(repasse_total) if repasse_total > 0 else "0,00"
        form["observacoes"] = ida_res.get("observacoes", "")
        form["mensagem"] = ""
        form["volta_mensagem"] = ""
        source = ida_res
    elif stored_tipo == "Por Hora":
        form["tipo"] = "Por Hora"
        form["hora_inicio"], form["hora_fim"] = _parse_trajeto_endpoints(reservation.get("trajeto"), reservation)
        form["hora_data"], form["hora_horario"] = _normalize_reservation_datetime(
            reservation.get("data"),
            reservation.get("hora"),
        )
        form["hora_passageiros"] = reservation.get("passageiros", "")
        form["hora_observacoes"] = reservation.get("observacoes", "")
        _apply_po_fields_to_form(form, reservation, "hora_inicio", "hora_fim")
        source = reservation
    else:
        form["tipo"] = _normalize_trip_type(stored_tipo)
        form["embarque"], form["desembarque"] = _parse_trajeto_endpoints(reservation.get("trajeto"), reservation)
        form["data"], form["hora"] = _normalize_reservation_datetime(reservation.get("data"), reservation.get("hora"))
        form["passageiros"] = reservation.get("passageiros") or "1"
        form["observacoes"] = reservation.get("observacoes", "")
        _apply_po_fields_to_form(form, reservation, "embarque", "desembarque")
        source = reservation

    form["motorista"] = _motorista_label_from_reservation(source)
    form["valor_base"] = (
        source.get("valor_base", "")
        or str(source.get("valor", "") or "").replace("R$", "").strip()
    )
    form["desconto"] = source.get("desconto", "0")
    form["pagamento"] = source.get("pagamento", "")
    form["status"] = source.get("status", "Pendente")
    form["faturado"] = "sim" if source.get("faturado") else "nao"
    form["esconder_valores"] = source.get("esconder_valores", "")
    if "repasse" not in form:
        form["repasse"] = source.get("repasse", "0,00")
    form["quem_faz"] = "Motorista"
    return form


def _prepare_values_from_form(app, form_data):
    values = {key: str(form_data.get(key, "") or "").strip() for key in form_data.keys()}
    values.update(collect_address_values_from_form(app, form_data, ADDRESS_KEYS))
    client_mode = str(form_data.get("client_mode", "novo") or "novo").strip().lower()
    if client_mode == "cadastrado":
        from .client_service import resolve_booking_customer

        selected = str(form_data.get("cliente_cadastrado", "") or "").strip()
        customer = resolve_booking_customer(app, selected)
        if customer:
            values["nome"] = customer["nome"]
            values["telefone"] = customer["telefone"]
            values["email"] = customer["email"]
            values["documento"] = customer["documento"]
            values["cliente_cadastro_id"] = customer.get("id", "")
            values["cliente_cadastro_tipo"] = customer.get("kind", "")
    return values, client_mode


def _replace_reservation_data(existing, new_data):
    preserved = {key: existing.get(key) for key in _PRESERVED_RESERVATION_KEYS if existing.get(key) is not None}
    existing.clear()
    existing.update(new_data)
    existing.update(preserved)


def _validate_create_payload(values, *, client_mode="novo", is_edit=False):
    required = {"valor_base": "Valor Base"}
    if str(client_mode or "novo").strip().lower() != "cadastrado":
        required["nome"] = "Nome Completo"
        if not is_edit:
            required.update(
                {
                    "documento": "CPF/CNPJ",
                    "email": "Email",
                    "telefone": "Telefone",
                }
            )
    trip_type = values.get("tipo", "Somente Ida")
    if trip_type == "Por Hora":
        required.update(
            {
                "hora_inicio": "Endereco de Inicio",
                "hora_fim": "Ponto de Encerramento",
                "hora_data": "Data",
                "hora_passageiros": "Passageiros",
                "qtd_horas": "Qtd. Horas",
            }
        )
        if not is_edit:
            required["hora_horario"] = "Hora de inicio"
    else:
        required.update(
            {
                "embarque": "Local de Embarque",
                "desembarque": "Local de Desembarque",
                "data": "Data do Embarque",
            }
        )
        if not is_edit:
            required.update(
                {
                    "hora": "Hora do Embarque",
                    "passageiros": "Passageiros",
                }
            )
        elif not str(values.get("passageiros", "") or "").strip():
            values["passageiros"] = "1"
        if trip_type == "Ida e Volta":
            required.update(
                {
                    "volta_embarque": "Local de Embarque (Volta)",
                    "volta_desembarque": "Local de Desembarque (Volta)",
                    "volta_data": "Data da Volta",
                }
            )
            if not is_edit:
                required["volta_hora"] = "Hora da Volta"

    for key, label in required.items():
        if not str(values.get(key, "") or "").strip():
            return False, f"Informe: {label}."

    if str(client_mode or "novo").strip().lower() == "cadastrado":
        if not str(values.get("nome", "") or "").strip():
            return False, "Selecione um cliente ou empresa cadastrada."
    elif not is_edit:
        ok, msg = validate_email_value(values.get("email"), label="Email")
        if not ok:
            return False, msg

        documento = re.sub(r"\D", "", str(values.get("documento", "")))
        if len(documento) not in {11, 14}:
            return False, "Informe um CPF (11 digitos) ou CNPJ (14 digitos) valido."

        telefone = re.sub(r"\D", "", str(values.get("telefone", "")))
        if len(telefone) < 10:
            return False, "Informe um telefone completo no formato (XX) X XXXX-XXXX."
    else:
        email = str(values.get("email", "") or "").strip()
        if email:
            ok, msg = validate_email_value(email, label="Email")
            if not ok:
                return False, msg
        documento = re.sub(r"\D", "", str(values.get("documento", "")))
        if documento and len(documento) not in {11, 14}:
            return False, "Informe um CPF (11 digitos) ou CNPJ (14 digitos) valido."
        telefone = re.sub(r"\D", "", str(values.get("telefone", "")))
        if telefone and len(telefone) < 10:
            return False, "Informe um telefone completo no formato (XX) X XXXX-XXXX."

    if not is_edit:
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
    values, client_mode = _prepare_values_from_form(app, form_data)

    ok, error = _validate_create_payload(values, client_mode=client_mode)
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
        **_billing_flags(form_data),
    }
    if values.get("cliente_cadastro_id"):
        common["cliente_cadastro_id"] = values["cliente_cadastro_id"]
        common["cliente_cadastro_tipo"] = values["cliente_cadastro_tipo"]

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
                **_route_fields(values["embarque"], values["desembarque"]),
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
                **_route_fields(values["volta_embarque"], values["volta_desembarque"]),
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
                **_route_fields(values["hora_inicio"], values["hora_fim"]),
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
                **_route_fields(values["embarque"], values["desembarque"]),
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

    values, client_mode = _prepare_values_from_form(app, form_data)
    ok, error = _validate_create_payload(values, client_mode=client_mode, is_edit=True)
    if not ok:
        return False, error

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
        **_billing_flags(form_data),
    }
    if values.get("cliente_cadastro_id"):
        common["cliente_cadastro_id"] = values["cliente_cadastro_id"]
        common["cliente_cadastro_tipo"] = values["cliente_cadastro_tipo"]

    trip_type = values.get("tipo", "Somente Ida")
    sibling = _find_pair_sibling(app, reservation)
    repasse_ida = repasse_total
    repasse_volta = 0.0
    if trip_type == "Ida e Volta" and repasse_total > 0:
        repasse_ida = round(repasse_total / 2, 2)
        repasse_volta = round(repasse_total - repasse_ida, 2)

    if trip_type == "Ida e Volta":
        ida_res = reservation if reservation.get("perna") == "ida" else sibling
        volta_res = sibling if reservation.get("perna") == "ida" else reservation
        if not ida_res or not volta_res:
            return False, "Par ida/volta incompleto — abra a reserva vinculada para editar."
        ida_data = values["data"]
        if values.get("hora"):
            ida_data = f"{ida_data} {values['hora']}"
        volta_data = values["volta_data"]
        if values.get("volta_hora"):
            volta_data = f"{volta_data} {values['volta_hora']}"
        ida_payload = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "embarque", "desembarque"),
                "tipo": "Ida",
                **_route_fields(values["embarque"], values["desembarque"]),
                "data": ida_data,
                "hora": values.get("hora", ""),
                "passageiros": values["passageiros"],
                "repasse": format_amount(repasse_ida) if repasse_ida > 0 else "0,00",
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("mensagem", "")])).strip(),
                "par_id": ida_res.get("par_id"),
                "perna": "ida",
            },
            motorista,
        )
        volta_payload = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "volta_embarque", "volta_desembarque"),
                "tipo": "Volta",
                **_route_fields(values["volta_embarque"], values["volta_desembarque"]),
                "data": volta_data,
                "hora": values.get("volta_hora", ""),
                "passageiros": values.get("volta_passageiros") or values["passageiros"],
                "repasse": format_amount(repasse_volta) if repasse_volta > 0 else "0,00",
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("volta_mensagem", "")])).strip(),
                "par_id": volta_res.get("par_id"),
                "perna": "volta",
            },
            motorista,
        )
        _replace_reservation_data(ida_res, ida_payload)
        _replace_reservation_data(volta_res, volta_payload)
    elif trip_type == "Por Hora":
        if sibling:
            return False, "Esta reserva faz parte de um par ida/volta — altere o tipo apenas pelo par vinculado."
        payload = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "hora_inicio", "hora_fim"),
                "tipo": values["tipo"],
                **_route_fields(values["hora_inicio"], values["hora_fim"]),
                "data": values["hora_data"],
                "hora": values.get("hora_horario", ""),
                "passageiros": values["hora_passageiros"],
                "observacoes": values.get("hora_observacoes", ""),
            },
            motorista,
        )
        _replace_reservation_data(reservation, payload)
    else:
        if sibling:
            app.reservations.remove(sibling)
        data = values["data"]
        hora = values.get("hora", "")
        if hora:
            data = f"{data} {hora}"
        payload = apply_finance_fields(
            {
                **common,
                **_reservation_location_meta(values, "embarque", "desembarque"),
                "tipo": values["tipo"],
                **_route_fields(values["embarque"], values["desembarque"]),
                "data": data,
                "hora": hora,
                "passageiros": values["passageiros"],
                "observacoes": "\n".join(filter(None, [values.get("observacoes", ""), values.get("mensagem", "")])).strip(),
            },
            motorista,
        )
        _replace_reservation_data(reservation, payload)

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
