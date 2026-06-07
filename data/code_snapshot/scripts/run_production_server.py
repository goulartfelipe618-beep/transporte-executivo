"""Servidor de producao headless (VPS) — gateway + motor de reservas."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _purge_pycache():
    for folder in ROOT.rglob("__pycache__"):
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    _purge_pycache()
    try:
        from app.code_guard import ensure_code_integrity

        ok, broken = ensure_code_integrity(auto_restore=True)
        if not ok:
            print("Arquivos ausentes:", ", ".join(broken))
            sys.exit(1)
    except ImportError:
        pass

    from app.production_runtime import run_production_forever

    run_production_forever()
