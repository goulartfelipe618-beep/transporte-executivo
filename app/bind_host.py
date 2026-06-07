"""Host de bind para servidores HTTP (local ou VPS)."""
from __future__ import annotations

import os

from .platform_contract import ENV_GATEWAY_HOST


def bind_host():
    raw = os.environ.get("NEXUS_BIND_HOST", "").strip() or os.environ.get(ENV_GATEWAY_HOST, "127.0.0.1").strip()
    return raw or "127.0.0.1"


def service_url(port, path=""):
    host = bind_host()
    display = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    base = f"http://{display}:{port}"
    return base + path if path else base
