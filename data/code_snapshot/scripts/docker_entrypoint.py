"""Entrypoint unico — EasyPanel pode ignorar Dockerfile.sistema e usar Dockerfile."""
import os
import sys


def _run_sistema():
    os.execvp(sys.executable, [sys.executable, "scripts/run_production_server.py"])


def _run_motor():
    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "8000")
    os.execvp(
        "uvicorn",
        ["uvicorn", "app.main:app", "--host", host, "--port", str(port)],
    )


def main():
    target = os.environ.get("NEXUS_DEPLOY_TARGET", "").strip().lower()
    print(f"[Nexus] docker_entrypoint NEXUS_DEPLOY_TARGET={target or 'motor'}")
    if target == "sistema":
        print("[Nexus] Iniciando Sistema Master (headless) porta 8770")
        _run_sistema()
    print("[Nexus] Iniciando Motor de Reservas (uvicorn)")
    _run_motor()


if __name__ == "__main__":
    main()
