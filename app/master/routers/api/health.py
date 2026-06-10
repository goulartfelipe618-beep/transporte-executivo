"""Endpoints de saude e deploy do Master Web."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.version import APP_BUILD

from ...config import get_settings

router = APIRouter(tags=["master-health"])


def _deploy_payload():
    settings = get_settings()
    try:
        stamp = Path("/app/.nexus_sistema_ui").read_text(encoding="utf-8").strip()
    except OSError:
        stamp = "unknown"
    return {
        "ok": True,
        "service": "master-web",
        "mode": "web",
        "build": APP_BUILD,
        "stamp": stamp,
        "vnc_removed": True,
        "login_url": "/login",
        "title": settings.app_title,
        "css_inline": True,
    }


@router.get("/health")
@router.get("/api/health")
@router.get("/api/v1/master/health")
async def health():
    return JSONResponse(
        {
            "ok": True,
            "service": "master-web",
            "build": APP_BUILD,
            "panel": True,
        },
        headers={"X-Nexus-Deploy": f"web-{APP_BUILD}"},
    )


@router.get("/api/deploy-info")
async def deploy_info():
    body = json.dumps(_deploy_payload(), ensure_ascii=False).encode("utf-8")
    return JSONResponse(
        content=json.loads(body),
        headers={
            "X-Nexus-Deploy": f"web-{APP_BUILD}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
