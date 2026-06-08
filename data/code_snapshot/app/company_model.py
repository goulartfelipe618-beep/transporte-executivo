"""Modelo de empresa corporativa e portal isolado por tenant."""
import re
import secrets
import string
from datetime import datetime

from .portal_urls import company_portal_link

COMPANY_USER_PROFILES = [
    "Administrador da Empresa",
    "Financeiro",
    "Solicitante",
    "Gestor",
]

COMPANY_USER_STATUSES = ["Ativo", "Inativo", "Pendente"]
COMPANY_STATUSES = ["Em analise", "Ativa", "Bloqueada"]
PORTAL_CODIGO_LEN = 12
_PORTAL_CODIGO_CHARS = string.ascii_uppercase + string.digits


def _timestamp():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def slugify(value):
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "empresa"


def company_key(company):
    return str(company.get("portal_key") or slugify(company.get("nome_fantasia") or company.get("razao_social") or company.get("id", "")))


def find_company(app, slug):
    slug = str(slug or "").strip().lower()
    for client in getattr(app, "clients", []):
        if client.get("tipo_pessoa") != "juridica":
            continue
        if company_key(client).lower() == slug or str(client.get("id", "")).lower() == slug:
            return client
    return None


def generate_portal_codigo(clients=None):
    used = {
        str(client.get("portal_codigo", "")).strip().upper()
        for client in clients or []
        if str(client.get("portal_codigo", "")).strip()
    }
    while True:
        codigo = "".join(secrets.choice(_PORTAL_CODIGO_CHARS) for _ in range(PORTAL_CODIGO_LEN))
        if codigo not in used:
            return codigo


def find_company_by_path(app, company_id, codigo):
    company_id = str(company_id or "").strip().lower()
    codigo = str(codigo or "").strip().upper()
    if not company_id or not codigo:
        return None
    for client in getattr(app, "clients", []):
        if client.get("tipo_pessoa") != "juridica":
            continue
        if str(client.get("id", "")).lower() != company_id:
            continue
        if str(client.get("portal_codigo", "")).strip().upper() == codigo:
            return client
    return None


def is_corporate_client(client):
    return client.get("tipo_pessoa") == "juridica" or bool(client.get("cnpj") or client.get("razao_social"))


def normalize_company_user(record, company_id):
    record = dict(record or {})
    perfil = record.get("perfil", "Solicitante")
    if perfil not in COMPANY_USER_PROFILES:
        perfil = "Solicitante"
    status = record.get("status", "Ativo")
    if status not in COMPANY_USER_STATUSES:
        status = "Ativo"
    user_id = record.get("id") or next_user_id(company_id, [])
    senha = record.get("senha") or secrets.token_urlsafe(8)
    return {
        "id": user_id,
        "company_id": company_id,
        "nome": str(record.get("nome", "")).strip(),
        "email": str(record.get("email", "")).strip().lower(),
        "telefone": str(record.get("telefone", "")).strip(),
        "senha": senha,
        "perfil": perfil,
        "status": status,
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or _timestamp(),
    }


def next_user_id(company_id, users):
    numbers = []
    for user in users:
        user_id = str(user.get("id", ""))
        if user_id.startswith("usr-"):
            try:
                numbers.append(int(user_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"usr-{max(numbers, default=0) + 1:03d}"


def next_company_id(clients):
    numbers = []
    for client in clients:
        client_id = str(client.get("id", ""))
        if client_id.startswith("emp-"):
            try:
                numbers.append(int(client_id.split("-", 1)[1]))
            except ValueError:
                pass
        elif client_id.startswith("cli-"):
            try:
                numbers.append(int(client_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"emp-{max(numbers, default=0) + 1:04d}"


def ensure_company_portal_structure(company, base_url, clients=None):
    company = dict(company or {})
    if not is_corporate_client(company):
        return company

    if not str(company.get("id", "")).startswith("emp-"):
        company["id"] = next_company_id(clients or [])

    company["tipo_pessoa"] = "juridica"
    company["portal_key"] = company.get("portal_key") or slugify(company.get("nome_fantasia") or company.get("razao_social") or company["id"])
    company["portal_ativo"] = bool(company.get("portal_ativo", True))
    company["status_empresa"] = company.get("status_empresa") or "Ativa"
    if company["status_empresa"] not in COMPANY_STATUSES:
        company["status_empresa"] = "Ativa"
    if not str(company.get("portal_codigo", "")).strip():
        company["portal_codigo"] = generate_portal_codigo(clients or [])
    else:
        company["portal_codigo"] = str(company["portal_codigo"]).strip().upper()[:PORTAL_CODIGO_LEN]
    link = company_portal_link(company)
    if not link and base_url:
        link = f"{str(base_url).rstrip('/')}/empresa/{company['portal_key']}"
    company["portal_link"] = link or company_portal_link(company)
    company["portal_criado_em"] = company.get("portal_criado_em") or _timestamp()

    users = [normalize_company_user(item, company["id"]) for item in company.get("usuarios") or []]
    if not users:
        admin_email = str(company.get("email", "")).strip().lower()
        if admin_email:
            users.append(
                normalize_company_user(
                    {
                        "nome": company.get("responsavel") or company.get("razao_social") or "Administrador",
                        "email": admin_email,
                        "telefone": company.get("telefone", ""),
                        "perfil": "Administrador da Empresa",
                        "status": "Ativo",
                    },
                    company["id"],
                )
            )
    company["usuarios"] = users
    company.setdefault("centros_custo", company.get("centros_custo") or [])
    company.setdefault("passageiros", company.get("passageiros") or [])
    company.setdefault("portal_activity", company.get("portal_activity") or [])
    return company


def next_cost_center_id(company_id, centros):
    numbers = []
    for item in centros:
        cc_id = str(item.get("id", ""))
        if cc_id.startswith("cc-"):
            try:
                numbers.append(int(cc_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"cc-{max(numbers, default=0) + 1:03d}"


def next_passenger_id(company_id, passengers):
    numbers = []
    for item in passengers:
        passenger_id = str(item.get("id", ""))
        if passenger_id.startswith("psg-"):
            try:
                numbers.append(int(passenger_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"psg-{max(numbers, default=0) + 1:04d}"


def normalize_cost_center(record, company_id, centros=None):
    record = dict(record or {})
    centros = list(centros or [])
    status = record.get("status", "Ativo")
    if status not in {"Ativo", "Inativo"}:
        status = "Ativo"
    saved = {
        "id": record.get("id") or next_cost_center_id(company_id, centros),
        "company_id": company_id,
        "nome": str(record.get("nome", "")).strip(),
        "codigo": str(record.get("codigo", "")).strip(),
        "status": status,
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": _timestamp(),
    }
    return saved


def normalize_passenger(record, company_id, passengers=None):
    record = dict(record or {})
    passengers = list(passengers or [])
    status = record.get("status", "Ativo")
    if status not in {"Ativo", "Inativo"}:
        status = "Ativo"
    saved = {
        "id": record.get("id") or next_passenger_id(company_id, passengers),
        "company_id": company_id,
        "nome": str(record.get("nome", "")).strip(),
        "email": str(record.get("email", "")).strip().lower(),
        "telefone": str(record.get("telefone", "")).strip(),
        "documento": str(record.get("documento", "")).strip(),
        "centro_custo_id": str(record.get("centro_custo_id", "")).strip(),
        "status": status,
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": _timestamp(),
    }
    return saved


def append_portal_activity(company, titulo, resumo, *, user_id="", referencia_id=""):
    company.setdefault("portal_activity", [])
    entry = {
        "titulo": str(titulo or "").strip(),
        "resumo": str(resumo or "").strip(),
        "user_id": str(user_id or ""),
        "referencia_id": str(referencia_id or ""),
        "criado_em": _timestamp(),
    }
    company["portal_activity"].insert(0, entry)
    company["portal_activity"] = company["portal_activity"][:50]
    return entry


def find_company_user(company, email):
    email = str(email or "").strip().lower()
    for user in company.get("usuarios") or []:
        if str(user.get("email", "")).lower() == email:
            return user
    return None


def company_reservations(app, company):
    company_id = company.get("id")
    company_name = company.get("razao_social") or company.get("nome_fantasia") or company.get("nome", "")
    items = []
    for reservation in getattr(app, "reservations", []):
        if reservation.get("company_id") == company_id:
            items.append(reservation)
            continue
        if company_name and reservation.get("cliente") == company_name:
            items.append(reservation)
    return items


def company_transport_requests(app, company):
    company_id = company.get("id")
    return [item for item in getattr(app, "transport_requests", []) if item.get("company_id") == company_id]
