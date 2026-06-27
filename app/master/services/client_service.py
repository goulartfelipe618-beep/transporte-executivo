"""CRUD de clientes pessoa fisica (PF) — separado de empresas corporativas."""
from __future__ import annotations

from app.company_model import is_corporate_client
from app.repository.ids import next_entity_id

from .location_service import apply_location_payload


def client_display_name(client):
    return str(client.get("nome") or client.get("nome_completo") or "").strip()


def client_document(client):
    return str(client.get("documento") or client.get("cpf") or client.get("cpf_cnpj") or "").strip()


def is_physical_client(client):
    if not client or is_corporate_client(client):
        return False
    return str(client.get("tipo_pessoa", "fisica")).lower() != "juridica"


def list_physical_clients(app, *, search=""):
    items = []
    query = str(search or "").strip().lower()
    for client in getattr(app, "clients", []) or []:
        if not is_physical_client(client):
            continue
        if query:
            haystack = " ".join(
                [
                    client_display_name(client),
                    client_document(client),
                    str(client.get("telefone", "")),
                    str(client.get("telefone_2", "")),
                    str(client.get("email", "")),
                    str(client.get("id", "")),
                ]
            ).lower()
            if query not in haystack:
                continue
        items.append(client)
    items.sort(key=lambda row: client_display_name(row).lower())
    return items


def find_physical_client(app, client_id):
    client_id = str(client_id or "").strip()
    for client in getattr(app, "clients", []) or []:
        if str(client.get("id", "")) == client_id and is_physical_client(client):
            return client
    return None


def list_summary(app):
    items = list_physical_clients(app)
    return {"total": len(items)}


def _collect_addresses(form_data):
    enderecos = []
    main_endereco = str(form_data.get("endereco", "")).strip()
    main_tipo = str(form_data.get("endereco_tipo", "casa")).strip() or "casa"
    if main_endereco:
        enderecos.append({"tipo": main_tipo, "endereco": main_endereco})
    extra = str(form_data.get("endereco_extra", "")).strip()
    if extra:
        enderecos.append({"tipo": "outro", "endereco": extra})
    return enderecos


def _build_payload(form_data, *, existing=None):
    existing = existing or {}
    payload = {
        "id": existing.get("id") or next_entity_id("cli", getattr(form_data, "_clients_ref", []) or []),
        "tipo_pessoa": "fisica",
        "nome": str(form_data.get("nome", "")).strip(),
        "nome_completo": str(form_data.get("nome", "")).strip(),
        "documento": str(form_data.get("documento", "")).strip(),
        "cpf": str(form_data.get("documento", "")).strip(),
        "cpf_cnpj": str(form_data.get("documento", "")).strip(),
        "email": str(form_data.get("email", "")).strip().lower(),
        "telefone": str(form_data.get("telefone", "")).strip(),
        "telefone_2": str(form_data.get("telefone_2", "")).strip(),
        "endereco_tipo": str(form_data.get("endereco_tipo", "casa")).strip() or "casa",
        "foto_perfil": str(form_data.get("foto_perfil", existing.get("foto_perfil", ""))).strip(),
    }
    apply_location_payload(payload, form_data, existing=existing)
    payload["enderecos"] = _collect_addresses(payload)
    return payload


def create_client(app, form_data):
    payload = _build_payload(form_data)
    payload["id"] = next_entity_id("cli", getattr(app, "clients", []) or [])
    clients = list(getattr(app, "clients", []) or [])
    clients.append(payload)
    app.clients = clients
    app.save_state()
    return payload


def update_client(app, client_id, form_data):
    client = find_physical_client(app, client_id)
    if not client:
        return None, "Cliente nao encontrado."
    payload = _build_payload(form_data, existing=client)
    client.update(payload)
    app.save_state()
    return client, ""


def delete_client(app, client_id):
    client = find_physical_client(app, client_id)
    if not client:
        return False, "Cliente nao encontrado."
    app.clients.remove(client)
    app.save_state()
    return True, ""


def booking_customer_options(app):
    """Opcoes para reserva: empresas PJ + clientes PF."""
    from .company_service import company_display_name, list_corporate_companies

    options = []
    for company in list_corporate_companies(app):
        label = company_display_name(company)
        options.append(
            {
                "value": f"emp:{company.get('id', '')}",
                "label": f"[Empresa] {label}",
                "kind": "empresa",
                "id": company.get("id", ""),
                "nome": label,
                "documento": company.get("cnpj") or company.get("documento", ""),
                "email": company.get("email", ""),
                "telefone": company.get("telefone", ""),
            }
        )
    for client in list_physical_clients(app):
        name = client_display_name(client)
        options.append(
            {
                "value": f"cli:{client.get('id', '')}",
                "label": f"[Cliente] {name}",
                "kind": "cliente",
                "id": client.get("id", ""),
                "nome": name,
                "documento": client_document(client),
                "email": client.get("email", ""),
                "telefone": client.get("telefone", ""),
            }
        )
    return options


def resolve_booking_customer(app, selection):
    selection = str(selection or "").strip()
    if not selection or ":" not in selection:
        return None
    kind, ref_id = selection.split(":", 1)
    if kind == "emp":
        from .company_service import find_company_by_id

        company = find_company_by_id(app, ref_id)
        if not company:
            return None
        from .company_service import company_display_name

        return {
            "kind": "empresa",
            "id": company.get("id", ""),
            "nome": company_display_name(company),
            "documento": company.get("cnpj") or company.get("documento", ""),
            "email": company.get("email", ""),
            "telefone": company.get("telefone", ""),
        }
    if kind == "cli":
        client = find_physical_client(app, ref_id)
        if not client:
            return None
        return {
            "kind": "cliente",
            "id": client.get("id", ""),
            "nome": client_display_name(client),
            "documento": client_document(client),
            "email": client.get("email", ""),
            "telefone": client.get("telefone", ""),
        }
    return None
