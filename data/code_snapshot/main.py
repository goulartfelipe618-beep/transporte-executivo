import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "data" / "code_snapshot"


def _restore_missing_from_snapshot():
    """Preenche apenas arquivos que NAO existem no disco — nunca sobrescreve edicoes novas."""
    if not SNAPSHOT.is_dir():
        return
    for src in SNAPSHOT.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(SNAPSHOT)
        dest = ROOT / rel
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _purge_pycache():
    for folder in ROOT.rglob("__pycache__"):
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    _purge_pycache()
    _restore_missing_from_snapshot()
    try:
        from app.code_guard import ensure_code_integrity

        ok, broken = ensure_code_integrity(auto_restore=True)
        if not ok:
            print("Arquivos ausentes ou corrompidos (sem marcador):", ", ".join(broken))
            print("Copie manualmente de data/code_snapshot/ se necessario.")
            sys.exit(1)
    except ImportError:
        _restore_missing_from_snapshot()

    from app.main_window import TransferSystemApp

    app = TransferSystemApp()
    app.mainloop()
