"""TOTP (RFC 6238) — autenticacao em dois fatores do Sistema Master."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import struct
import time
from urllib.parse import quote

from .settings_store import load_settings, save_settings

SECURITY_FIELDS = ("totp_secret", "totp_enabled", "totp_enabled_em")
TOTP_ISSUER = "Transporte Executivo"


def generate_totp_secret() -> str:
    raw = secrets.token_bytes(20)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    padded = str(secret or "").upper().replace(" ", "")
    pad = (8 - len(padded) % 8) % 8
    return base64.b32decode(padded + ("=" * pad))


def totp_at(secret: str, *, for_time: int | None = None, digits: int = 6, period: int = 30) -> str:
    counter = int((for_time if for_time is not None else time.time()) // period)
    key = _decode_secret(secret)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def verify_totp_code(secret: str, code: str, *, window: int = 1) -> bool:
    normalized = str(code or "").strip().replace(" ", "")
    if not normalized.isdigit() or len(normalized) != 6:
        return False
    now = int(time.time())
    for step in range(-window, window + 1):
        if totp_at(secret, for_time=now + step * 30) == normalized:
            return True
    return False


def provisioning_uri(secret: str, account_name: str, *, issuer: str = TOTP_ISSUER) -> str:
    account = str(account_name or "admin").strip() or "admin"
    label = quote(f"{issuer}:{account}")
    params = (
        f"secret={secret}&issuer={quote(issuer)}"
        "&algorithm=SHA1&digits=6&period=30"
    )
    return f"otpauth://totp/{label}?{params}"


def totp_qr_data_url(uri: str) -> str:
    import qrcode

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def is_totp_enabled(settings=None) -> bool:
    data = settings if settings is not None else load_settings()
    flag = str(data.get("totp_enabled", "")).strip().lower()
    secret = str(data.get("totp_secret", "")).strip()
    return flag in {"sim", "1", "true", "yes", "on"} and bool(secret)


def totp_status(settings=None) -> dict:
    data = settings if settings is not None else load_settings()
    enabled = is_totp_enabled(data)
    return {
        "enabled": enabled,
        "enabled_em": str(data.get("totp_enabled_em", "") or ""),
        "account": str(data.get("email", "") or data.get("email_oficial", "") or "admin"),
    }


def verify_action_totp(code: str, settings=None) -> tuple[bool, str]:
    data = settings if settings is not None else load_settings()
    if not is_totp_enabled(data):
        return False, "Configure o 2FA em Sistema > Configuracoes antes de executar esta acao."
    secret = str(data.get("totp_secret", "")).strip()
    if verify_totp_code(secret, code):
        return True, ""
    return False, "Codigo 2FA invalido ou expirado. Tente novamente."


def enable_totp(secret: str, code: str, *, account_email: str = "") -> tuple[bool, str]:
    secret = str(secret or "").strip()
    if not secret:
        return False, "Secret TOTP ausente."
    if not verify_totp_code(secret, code):
        return False, "Codigo invalido. Confira o aplicativo autenticador e tente novamente."
    data = load_settings()
    data["totp_secret"] = secret
    data["totp_enabled"] = "sim"
    data["totp_enabled_em"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if account_email:
        data.setdefault("email", account_email)
    save_settings(data)
    return True, ""


def disable_totp(code: str) -> tuple[bool, str]:
    data = load_settings()
    ok, message = verify_action_totp(code, data)
    if not ok:
        return False, message
    data["totp_secret"] = ""
    data["totp_enabled"] = "nao"
    data["totp_enabled_em"] = ""
    save_settings(data)
    return True, ""


def merge_security_fields(payload: dict, existing: dict | None = None) -> dict:
    source = existing if existing is not None else load_settings()
    merged = dict(payload)
    for key in SECURITY_FIELDS:
        if key not in merged and key in source:
            merged[key] = source[key]
    return merged
