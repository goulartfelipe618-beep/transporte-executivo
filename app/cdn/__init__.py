"""Armazenamento de mídia — Cloudflare R2 + CDN."""
from .storage import (
    is_r2_configured,
    sync_driver_media,
    sync_record_media,
    sync_settings_media,
    sync_vehicle_media,
    upload_bytes,
    upload_local_file,
    upload_qr_png,
)
from .urls import cdn_base, cdn_enabled, patch_css_static_urls, resolve_media_url, static_url

__all__ = [
    "cdn_base",
    "cdn_enabled",
    "is_r2_configured",
    "patch_css_static_urls",
    "resolve_media_url",
    "static_url",
    "sync_driver_media",
    "sync_record_media",
    "sync_settings_media",
    "sync_vehicle_media",
    "upload_bytes",
    "upload_local_file",
    "upload_qr_png",
]
