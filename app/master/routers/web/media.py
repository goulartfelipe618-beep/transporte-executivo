"""Rotas web — midia configurada (logo, assinatura) servivel ao navegador."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.cdn.storage import generate_presigned_url
from app.cdn.urls import resolve_media_url
from app.settings_store import load_settings

router = APIRouter(tags=["master-media"])

_BRANDING_FIELDS = {
    "logo": "logo_global",
    "logo-contratual": "logo_contratual",
    "assinatura": "assinatura",
}


def _resolve_branding_path(field: str) -> str:
    key = _BRANDING_FIELDS.get(field)
    if not key:
        raise HTTPException(status_code=404, detail="Midia nao encontrada.")
    return str(load_settings().get(key) or "").strip()


def _file_response(path: Path) -> FileResponse:
    mime, _ = mimetypes.guess_type(str(path))
    return FileResponse(path, media_type=mime or "application/octet-stream")


@router.get("/media/branding/{field}")
async def branding_media(field: str):
    stored = _resolve_branding_path(field)
    if not stored:
        raise HTTPException(status_code=404, detail="Midia nao configurada.")

    if stored.startswith("r2private:"):
        key = stored[len("r2private:"):].lstrip("/")
        signed = generate_presigned_url(key)
        if not signed:
            raise HTTPException(status_code=503, detail="CDN indisponivel.")
        return RedirectResponse(signed, status_code=307)

    resolved = resolve_media_url(stored)
    if resolved.startswith(("http://", "https://")):
        return RedirectResponse(resolved, status_code=307)

    path = Path(stored).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")
    return _file_response(path)
