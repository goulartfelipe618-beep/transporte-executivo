"""Captcha simples para tela de login web."""
from __future__ import annotations

import secrets
import string

_CAPTCHA_ALPHABET = string.ascii_letters + string.digits
_CAPTCHA_ALPHABET = "".join(ch for ch in _CAPTCHA_ALPHABET if ch not in "0O1lI")


def new_captcha_code(length: int = 6) -> str:
    return "".join(secrets.choice(_CAPTCHA_ALPHABET) for _ in range(length))


def store_login_captcha(request, code: str) -> None:
    request.session["login_captcha"] = str(code or "").strip()


def peek_login_captcha(request) -> str:
    return str(request.session.get("login_captcha", "") or "").strip()


def verify_login_captcha(request, value: str) -> bool:
    expected = str(request.session.pop("login_captcha", "") or "").strip()
    provided = str(value or "").strip()
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected, provided)
