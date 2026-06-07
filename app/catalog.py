"""Entidades administrativas de rede: hoteis, aeroportos e parceiros."""
from datetime import datetime

HOTEL_CATEGORIES = ["Economico", "Executivo", "Luxo", "Resort"]
NETWORK_TYPES = ["Hotel", "Centro de Eventos", "Operador", "Parceiro Corporativo"]
PUBLISH_STATUSES = ["Publicado", "Rascunho", "Inativo"]


def _timestamp():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def next_record_id(prefix, records):
    numbers = []
    for item in records:
        record_id = str(item.get("id", ""))
        if record_id.startswith(f"{prefix}-"):
            try:
                numbers.append(int(record_id.split("-", 1)[1]))
            except ValueError:
                pass
    return f"{prefix}-{max(numbers, default=0) + 1:04d}"


def normalize_hotel(record):
    record = dict(record or {})
    categoria = record.get("categoria", "Executivo")
    if categoria not in HOTEL_CATEGORIES:
        categoria = "Executivo"
    status = record.get("status", "Publicado")
    if status not in PUBLISH_STATUSES:
        status = "Publicado"
    return {
        "id": record.get("id") or next_record_id("htl", []),
        "nome": str(record.get("nome", "")).strip(),
        "cidade": str(record.get("cidade", "")).strip(),
        "estado": str(record.get("estado", "")).upper().strip(),
        "categoria": categoria,
        "endereco": str(record.get("endereco", "")).strip(),
        "contato": str(record.get("contato", "")).strip(),
        "observacoes": str(record.get("observacoes", "")).strip(),
        "status": status,
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or _timestamp(),
    }


def normalize_airport(record):
    record = dict(record or {})
    status = record.get("status", "Publicado")
    if status not in PUBLISH_STATUSES:
        status = "Publicado"
    return {
        "id": record.get("id") or next_record_id("apt", []),
        "nome": str(record.get("nome", "")).strip(),
        "cidade": str(record.get("cidade", "")).strip(),
        "estado": str(record.get("estado", "")).upper().strip(),
        "codigo_iata": str(record.get("codigo_iata", "")).upper().strip(),
        "observacoes": str(record.get("observacoes", "")).strip(),
        "status": status,
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or _timestamp(),
    }


def normalize_network(record):
    record = dict(record or {})
    tipo = record.get("tipo", "Parceiro Corporativo")
    if tipo not in NETWORK_TYPES:
        tipo = "Parceiro Corporativo"
    status = record.get("status", "Publicado")
    if status not in PUBLISH_STATUSES:
        status = "Publicado"
    return {
        "id": record.get("id") or next_record_id("net", []),
        "nome": str(record.get("nome", "")).strip(),
        "tipo": tipo,
        "cidade": str(record.get("cidade", "")).strip(),
        "estado": str(record.get("estado", "")).upper().strip(),
        "contato": str(record.get("contato", "")).strip(),
        "observacoes": str(record.get("observacoes", "")).strip(),
        "status": status,
        "criado_em": record.get("criado_em") or _timestamp(),
        "atualizado_em": record.get("atualizado_em") or _timestamp(),
    }


def published_items(items):
    return [item for item in items if item.get("status") == "Publicado"]
