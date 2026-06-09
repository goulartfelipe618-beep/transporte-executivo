"""Servico de configuracoes do Sistema Master — espelha full_features.render_settings."""
from __future__ import annotations

from app.branding import apply_branding, brand_display_name, resolve_font_family
from app.settings_store import DEFAULT_SETTINGS, SETTINGS_FIELDS, load_settings, save_settings

from ..validators.input import validate_email_value

PROFILE_FIELDS = (
    ("nome_completo", "Nome completo", "Nome completo", True),
    ("email", "E-mail", "email@empresa.com", True),
    ("telefone", "Telefone", "Telefone", True),
    ("empresa", "Nome da empresa", "Nome da empresa", True),
    ("cnpj_opcional", "CNPJ (opcional)", "CNPJ", False),
    ("cidade", "Cidade", "Cidade", True),
    ("uf", "Estado (UF)", "UF", True),
    ("endereco_completo", "Endereco completo", "Endereco completo", True),
)

BRAND_FIELDS = (
    ("nome_projeto", "Nome global do sistema", "DRIVE PREMIUM", True),
    ("fonte_global", "Fonte global", "Poppins", True),
)

CONTRACT_FIELDS = (
    ("razao_social", "Razao social", "Razao social", True),
    ("cnpj_contrato", "CNPJ", "CNPJ", True),
    ("endereco_sede", "Endereco da sede", "Endereco", True),
    ("representante_legal", "Representante legal", "Nome", True),
    ("telefone_contrato", "Telefone", "Telefone", True),
    ("whatsapp_contrato", "WhatsApp", "WhatsApp", True),
    ("email_oficial", "E-mail oficial", "E-mail", True),
    ("logo_contratual", "Logo contratual", "Caminho da imagem", False),
)

FILE_FIELDS = ("logo_global", "assinatura", "logo_contratual")


def display_file_value(path):
    raw = str(path or "").strip()
    if not raw:
        return "Nenhum arquivo configurado"
    if len(raw) > 80:
        return "(arquivo configurado)"
    return raw


def normalize_form_payload(form_data):
    payload = dict(DEFAULT_SETTINGS)
    payload.update(load_settings())
    for key in SETTINGS_FIELDS:
        if key in form_data:
            payload[key] = str(form_data.get(key, "")).strip()
    return payload


def validate_settings_form(form_data):
    errors = []
    data = normalize_form_payload(form_data)

    for key, label, _placeholder, required in PROFILE_FIELDS + BRAND_FIELDS:
        if required and not str(data.get(key, "")).strip():
            errors.append(f"Informe: {label}.")

    for key, label, _placeholder, required in CONTRACT_FIELDS:
        if required and not str(data.get(key, "")).strip():
            errors.append(f"Informe: {label}.")

    for key in ("email", "email_oficial"):
        value = str(data.get(key, "")).strip()
        if value:
            ok, message = validate_email_value(value, label="E-mail" if key == "email" else "E-mail oficial")
            if not ok:
                errors.append(message)

    possui = str(data.get("possui_cnpj", "sim")).strip().lower()
    if possui not in {"sim", "nao"}:
        errors.append("Selecione se a empresa possui CNPJ.")

    return errors, data


def font_warning_message(requested_font):
    requested = str(requested_font or "").strip()
    if not requested:
        return ""
    resolved = resolve_font_family(requested)
    if resolved == "Segoe UI" and requested.lower() not in {"segoe ui", "segoe"}:
        return (
            f'A fonte "{requested}" nao esta instalada no sistema. '
            "Usando Segoe UI. Instale a fonte e reinicie para aplicar."
        )
    return ""


def update_settings(form_data):
    errors, payload = validate_settings_form(form_data)
    if errors:
        return None, errors, ""

    save_settings(payload)
    try:
        apply_branding(payload)
    except (RuntimeError, ImportError, OSError):
        pass
    return payload, [], font_warning_message(payload.get("fonte_global", ""))


def settings_page_context(*, editing=False, form=None, error="", saved=False, warning=""):
    data = dict(form or load_settings())
    preview_name = str(data.get("nome_projeto") or "Projeto").strip() or "Projeto"
    preview_font = str(data.get("fonte_global") or "Segoe UI").strip() or "Segoe UI"
    return {
        "settings": data,
        "editing": editing,
        "error": error,
        "saved": saved,
        "warning": warning,
        "profile_fields": PROFILE_FIELDS,
        "brand_fields": BRAND_FIELDS,
        "contract_fields": CONTRACT_FIELDS,
        "file_fields": FILE_FIELDS,
        "display_file": display_file_value,
        "pills": [
            ("Projeto", data.get("nome_projeto") or "-"),
            ("Empresa", data.get("empresa") or "-"),
            ("Contato", data.get("email") or "-"),
        ],
        "preview_text": f"Preview: {preview_name} — fonte {preview_font}",
        "preview_font": preview_font,
        "brand_name": brand_display_name(data),
    }
