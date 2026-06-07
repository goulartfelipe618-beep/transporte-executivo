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


def _is_sistema_mode() -> bool:
    target = os.environ.get("NEXUS_DEPLOY_TARGET", "").strip().lower()
    if target == "sistema":
        return True
    service = os.environ.get("SERVICE_NAME", "").strip().lower()
    if "sistema" in service:
        return True
    domain = (
        os.environ.get("PRIMARY_DOMAIN", "")
        + os.environ.get("EASYPANEL_DOMAIN", "")
    )
    return "api.transporteexecutivo.com" in domain


def main():
    if _is_sistema_mode():
        target = os.environ.get("NEXUS_DEPLOY_TARGET", "").strip().lower() or "api-domain"
        print(f"[Nexus] docker_entrypoint modo sistema ({target})")
        print("[Nexus] Iniciando Sistema Master (headless) porta 8770")
        _run_sistema()
    print("[Nexus] docker_entrypoint modo motor")
    print("[Nexus] Iniciando Motor de Reservas (uvicorn)")
    _run_motor()


if __name__ == "__main__":
    main()
