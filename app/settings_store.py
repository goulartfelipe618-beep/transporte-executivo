import json
import os

SETTINGS_FILE = os.path.join("data", "settings.json")
SETTINGS_KEY = "master_settings"

SETTINGS_FIELDS = (
    "nome_completo", "email", "telefone", "empresa", "cnpj_opcional", "cidade", "uf",
    "endereco_completo", "logo_global", "nome_projeto", "fonte_global", "possui_cnpj",
    "razao_social", "cnpj_contrato", "endereco_sede", "representante_legal",
    "telefone_contrato", "whatsapp_contrato", "email_oficial", "logo_contratual", "assinatura",
)

DEFAULT_SETTINGS = {field: "" for field in SETTINGS_FIELDS}


def _empty_settings():
    return dict(DEFAULT_SETTINGS)


def _load_supabase_settings():
    from .repository.supabase_client import is_configured, select_one

    if not is_configured():
        raise RuntimeError("Supabase obrigatorio para carregar configuracoes.")
    row = select_one("settings", {"chave": SETTINGS_KEY})
    if row and isinstance(row.get("valor"), dict):
        merged = _empty_settings()
        merged.update(row["valor"])
        return merged
    return _empty_settings()


def load_settings():
    from .repository.supabase_client import is_configured

    if is_configured():
        try:
            return _load_supabase_settings()
        except RuntimeError:
            pass
    return _load_local_settings()


def save_settings(data):
    from .repository.supabase_client import is_configured, upsert_row
    from .totp_auth import merge_security_fields

    existing = load_settings()
    merged = merge_security_fields(dict(data), existing)

    if not is_configured():
        _write_local_settings(merged)
        return

    upsert_row(
        "settings",
        {"chave": SETTINGS_KEY, "valor": merged, "descricao": "Configuracoes Sistema Master"},
        on_conflict="chave",
    )

    _write_local_settings(merged)


def _load_local_settings():
    if not os.path.isfile(SETTINGS_FILE):
        return _empty_settings()
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as handle:
            raw = json.load(handle)
        if isinstance(raw, dict):
            merged = _empty_settings()
            merged.update(raw)
            return merged
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_settings()


def _write_local_settings(data):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
