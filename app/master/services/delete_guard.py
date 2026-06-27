"""Fluxo padrao de exclusao com confirmacao 2FA no Master Web."""
from __future__ import annotations

from app.totp_auth import is_totp_enabled, verify_action_totp

from ..dependencies import template_context, templates


def delete_confirm_response(
    request,
    admin,
    *,
    active_nav: str,
    entity_title: str,
    entity_name: str,
    entity_id: str,
    cancel_url: str,
    post_url: str,
    warning_message: str,
    error: str = "",
    status_code: int = 200,
    **extra_context,
):
    ctx = template_context(
        request,
        admin=admin,
        active_nav=active_nav,
        entity_title=entity_title,
        entity_name=entity_name,
        entity_id=entity_id,
        cancel_url=cancel_url,
        post_url=post_url,
        warning_message=warning_message,
        totp_enabled=is_totp_enabled(),
        error=error,
        **extra_context,
    )
    return templates.TemplateResponse(
        request,
        "master/_delete_confirm_2fa.html",
        ctx,
        status_code=status_code,
    )


def verify_delete_confirmation(form_data, expected_id: str) -> tuple[bool, str]:
    confirm_id = str(form_data.get("confirm_id", "")).strip()
    totp_code = str(form_data.get("totp_code", "")).strip()
    if confirm_id != str(expected_id):
        return False, "Identificador nao confere. Digite exatamente o valor indicado para confirmar."
    ok, err = verify_action_totp(totp_code)
    if not ok:
        return False, err
    return True, ""
