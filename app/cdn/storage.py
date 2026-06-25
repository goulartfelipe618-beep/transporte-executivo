"""Upload e gestão de objetos no Cloudflare R2."""
from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from pathlib import Path
from typing import BinaryIO

from .config import get_r2_config

_PRIVATE_PREFIX = "private/"
_CLIENT = None

DRIVER_MEDIA_FIELDS = ("foto_perfil", "cnh_frente", "cnh_verso", "comprovante_residencia")
DRIVER_PRIVATE_FIELDS = frozenset({"cnh_frente", "cnh_verso", "comprovante_residencia"})
VEHICLE_MEDIA_FIELDS = (
    "capa",
    "img_dianteira",
    "img_traseira",
    "img_lateral_esquerda",
    "img_lateral_direita",
    "img_externa_1",
    "img_externa_2",
    "img_externa_3",
    "img_externa_4",
    "img_interna_1",
    "img_interna_2",
    "img_interna_3",
    "img_interna_4",
)
SETTINGS_MEDIA_FIELDS = ("logo_global", "logo_contratual", "assinatura")


def is_r2_configured() -> bool:
    return get_r2_config()["configured"]


def _slug(value: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "asset").strip().lower())
    return raw.strip("-") or "asset"


def object_key(*parts: str) -> str:
    cfg = get_r2_config()
    cleaned = [_slug(part) if idx == 0 else str(part).strip("/") for idx, part in enumerate(parts) if str(part).strip()]
    key = "/".join(cleaned)
    if cfg["prefix"]:
        return f"{cfg['prefix']}/{key}"
    return key


def public_url_for_key(key: str) -> str:
    cfg = get_r2_config()
    key = str(key or "").lstrip("/")
    return f"{cfg['public_base']}/{key}"


def _get_client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    cfg = get_r2_config()
    if not cfg["configured"]:
        return None
    import boto3

    _CLIENT = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name="auto",
    )
    return _CLIENT


def _guess_content_type(path: Path | str) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def upload_bytes(
    data: bytes | BinaryIO,
    key: str,
    *,
    content_type: str = "application/octet-stream",
    public: bool = True,
) -> str:
    cfg = get_r2_config()
    client = _get_client()
    if not client:
        raise RuntimeError("R2 nao configurado. Defina R2_ACCESS_KEY_ID e R2_SECRET_ACCESS_KEY.")
    body = data.read() if hasattr(data, "read") else data
    extra = {}
    if public:
        extra["CacheControl"] = "public, max-age=31536000, immutable"
    client.put_object(
        Bucket=cfg["bucket"],
        Key=key,
        Body=body,
        ContentType=content_type,
        **extra,
    )
    if public:
        return public_url_for_key(key)
    return f"r2private:{key}"


def upload_local_file(
    local_path: str | Path,
    key: str,
    *,
    public: bool = True,
    content_type: str | None = None,
) -> str:
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    mime = content_type or _guess_content_type(path)
    return upload_bytes(path.read_bytes(), key, content_type=mime, public=public)


def generate_presigned_url(key: str, *, expires: int | None = None) -> str:
    cfg = get_r2_config()
    client = _get_client()
    if not client:
        return ""
    key = str(key or "").lstrip("/")
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": cfg["bucket"], "Key": key},
        Expires=expires or cfg["signed_expires"],
    )


def _should_upload(value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    if raw.startswith(("http://", "https://", "r2private:")):
        return False
    return os.path.isfile(raw)


def upload_media_value(
    value: str,
    *,
    category: str,
    entity_id: str,
    field_name: str,
    public: bool = True,
) -> str:
    raw = str(value or "").strip()
    if not _should_upload(raw):
        return raw
    cfg = get_r2_config()
    if not cfg["configured"] or not cfg["auto_upload"]:
        return raw
    path = Path(raw)
    digest = hashlib.sha1(path.read_bytes()).hexdigest()[:10]
    ext = path.suffix.lower() or ".bin"
    visibility = "public" if public else _PRIVATE_PREFIX.rstrip("/")
    key = object_key(visibility, category, _slug(entity_id or "unknown"), f"{_slug(field_name)}-{digest}{ext}")
    return upload_local_file(path, key, public=public)


def sync_record_media(
    record: dict,
    fields: tuple[str, ...],
    *,
    category: str,
    entity_id: str,
    private_fields: frozenset[str] | None = None,
) -> dict:
    private_fields = private_fields or frozenset()
    entity = str(entity_id or record.get("id") or record.get("uuid") or "unknown")
    for field in fields:
        if field not in record:
            continue
        record[field] = upload_media_value(
            record.get(field, ""),
            category=category,
            entity_id=entity,
            field_name=field,
            public=field not in private_fields,
        )
    return record


def sync_driver_media(record: dict) -> dict:
    entity = str(record.get("id") or record.get("uuid") or record.get("cpf") or record.get("nome") or "driver")
    return sync_record_media(
        record,
        DRIVER_MEDIA_FIELDS,
        category="drivers",
        entity_id=entity,
        private_fields=DRIVER_PRIVATE_FIELDS,
    )


def sync_vehicle_media(record: dict) -> dict:
    entity = str(record.get("id") or record.get("uuid") or record.get("placa") or "vehicle")
    return sync_record_media(record, VEHICLE_MEDIA_FIELDS, category="vehicles", entity_id=entity)


def sync_settings_media(settings: dict) -> dict:
    entity = "master"
    return sync_record_media(settings, SETTINGS_MEDIA_FIELDS, category="logos", entity_id=entity)


def upload_static_file(local_path: Path, r2_relative: str) -> str:
    key = object_key("static", r2_relative.replace("\\", "/").lstrip("/"))
    return upload_local_file(local_path, key, public=True)


def upload_qr_png(data: bytes, partner_id: str) -> str:
    key = object_key("generated", "qrcodes", f"{_slug(partner_id)}.png")
    return upload_bytes(data, key, content_type="image/png", public=True)
