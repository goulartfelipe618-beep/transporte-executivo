#!/usr/bin/env python3
"""Envia assets estaticos locais para Cloudflare R2 (CDN)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.cdn.config import get_r2_config
from app.cdn.storage import is_r2_configured, upload_static_file


def _iter_static_files():
    motor_root = ROOT / "app" / "static"
    if motor_root.is_dir():
        for path in motor_root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(motor_root).as_posix()
                yield path, f"motor/{rel}"

    master_root = ROOT / "app" / "master" / "static" / "master"
    if master_root.is_dir():
        for path in master_root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(master_root).as_posix()
                yield path, f"master/{rel}"


def main() -> int:
    cfg = get_r2_config()
    if not is_r2_configured():
        print("R2 nao configurado. Defina R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY e R2_ACCOUNT_ID no .env")
        return 1

    uploaded = 0
    for local_path, r2_relative in _iter_static_files():
        url = upload_static_file(local_path, r2_relative)
        print(f"OK  {r2_relative} -> {url}")
        uploaded += 1

    print(f"\nConcluido: {uploaded} arquivo(s) em {cfg['public_base']}/{cfg['prefix']}/static/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
