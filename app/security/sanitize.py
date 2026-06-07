"""Input sanitization."""

import re

import bleach

ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}


def sanitize_html(value: str) -> str:
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


def sanitize_text(value: str, max_length: int = 2000) -> str:
    cleaned = sanitize_html(value.strip())
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    return cleaned[:max_length]


def sanitize_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)[:11]


def sanitize_phone(phone: str) -> str:
    return re.sub(r"[^\d+\-\s()]", "", phone)[:32]
