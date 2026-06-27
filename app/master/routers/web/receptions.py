"""Rotas web — Receptivos (plaquinhas de aeroporto/embarque)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from ...dependencies import get_runtime, resolve_admin_or_redirect, template_context, templates
from ...services.reception_service import (
    create_reception,
    find_reception,
    list_receptions,
    model_options,
    reservation_options,
)

router = APIRouter(prefix="/receptivos", tags=["master-receptivos"])


def _form_dict(form):
    return {key: form.get(key, "") for key in form.keys()}


@router.get("")
async def list_page(request: Request, success: str = ""):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        request,
        "master/receptivos/list.html",
        template_context(
            request,
            admin=admin,
            active_nav="receptivos",
            items=list_receptions(),
            success=success,
        ),
    )


@router.get("/novo")
async def create_form(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    return templates.TemplateResponse(
        request,
        "master/receptivos/form.html",
        template_context(
            request,
            admin=admin,
            active_nav="receptivos",
            models=model_options(),
            reservations=reservation_options(runtime),
            form={"include_details": "1"},
            error="",
        ),
    )


@router.post("/novo")
async def create_submit(request: Request):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    runtime = get_runtime(request)
    form_data = _form_dict(await request.form())
    item, error = create_reception(runtime, form_data)
    if error:
        return templates.TemplateResponse(
            request,
            "master/receptivos/form.html",
            template_context(
                request,
                admin=admin,
                active_nav="receptivos",
                models=model_options(),
                reservations=reservation_options(runtime),
                form=form_data,
                error=error,
            ),
            status_code=400,
        )
    return RedirectResponse(f"/receptivos?success={item['id']}", status_code=303)


@router.get("/{reception_id}/download")
async def download_pdf(request: Request, reception_id: str):
    admin, redirect = resolve_admin_or_redirect(request)
    if redirect:
        return redirect
    item = find_reception(reception_id)
    if not item:
        return RedirectResponse("/receptivos", status_code=303)
    path = Path(item.get("pdf_path", ""))
    if not path.is_file():
        return RedirectResponse("/receptivos", status_code=303)
    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=item.get("pdf_filename") or f"{reception_id}.pdf",
    )
