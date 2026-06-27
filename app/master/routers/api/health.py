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
    try:
        git_commit = Path("/app/.nexus_git_commit").read_text(encoding="utf-8").strip()
    except OSError:
        git_commit = ""
    form_unified = Path("/app/app/master/templates/master/reservations/form.html").is_file()
    form_legacy = Path("/app/app/master/templates/master/reservations/form_edit.html").is_file()
    receptivos = Path("/app/app/master/routers/web/receptions.py").is_file()
    try:
        cache_bust = Path("/app/.nexus_cache_bust").read_text(encoding="utf-8").strip()
    except OSError:
        cache_bust = ""
    return {
        "ok": True,
        "service": "master-web",
        "mode": "web",
        "build": APP_BUILD,
        "git_commit": git_commit,
        "stamp": stamp,
        "cache_bust": cache_bust,
        "vnc_removed": True,
        "login_url": "/login",
        "title": settings.app_title,
        "css_inline": True,
        "reservation_form_unified": form_unified and not form_legacy,
        "receptivos_module": receptivos,
        "expected_build": APP_BUILD,
        "required_commit_min": "92955ed",
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
