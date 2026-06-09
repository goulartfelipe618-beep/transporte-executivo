"""Servidor standalone Master Web (porta 8772)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    import uvicorn

    from app.bind_host import bind_host
    from app.master.config import get_settings
    from app.master.main import create_master_app
    from app.production_runtime import RuntimeApp

    runtime = RuntimeApp()
    settings = get_settings()
    app = create_master_app(runtime)
    host = bind_host()
    print(f"[Nexus] Master Web standalone — http://127.0.0.1:{settings.port} (bind {host})")
    uvicorn.run(app, host=host, port=settings.port, log_level="info")
