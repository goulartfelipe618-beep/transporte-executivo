"""Entrypoint unico — EasyPanel pode ignorar Dockerfile.sistema e usar Dockerfile."""
import os
import sys
from pathlib import Path


def _read_app_build():
    try:
        for line in Path("/app/app/version.py").read_text(encoding="utf-8").splitlines():
            if line.startswith("APP_BUILD"):
                return line.split("=", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return "desconhecido"


def _verify_sistema_bundle():
    app_dir = Path("/app/app")
    auth_file = app_dir / "admin_auth.py"
    sistema_file = app_dir / "sistema_web.py"
    if not auth_file.is_file():
        print("[Nexus] ERRO: admin_auth.py ausente na imagem. Faca rebuild no EasyPanel (branch main).")
        sys.exit(1)
    try:
        sistema_src = sistema_file.read_text(encoding="utf-8")
    except OSError:
        print("[Nexus] ERRO: sistema_web.py ausente na imagem.")
        sys.exit(1)
    if "from .admin_login import authenticate_admin" in sistema_src:
        print("[Nexus] ERRO: imagem desatualizada — sistema_web ainda importa admin_login (Tkinter).")
        sys.exit(1)
    if "/vnc.html" not in sistema_src:
        print("[Nexus] ERRO: sistema_web sem redirect /vnc.html — imagem antiga.")
        sys.exit(1)
    build = _read_app_build()
    commit = os.environ.get("NEXUS_GIT_COMMIT", "").strip()
    stamp = f"{build}" + (f" ({commit[:7]})" if commit else "")
    print(f"[Nexus] Bundle WEB validado — build {stamp}")


def _run_sistema():
    ui = os.environ.get("NEXUS_SISTEMA_UI", "web").strip().lower()
    if ui == "vnc":
        print("[Nexus] AVISO: NEXUS_SISTEMA_UI=vnc esta OBSOLETO — remova no EasyPanel.")
        print("[Nexus] VNC foi desligado. Subindo painel WEB na porta 8772.")
    build = _read_app_build()
    print(f"[Nexus] Painel WEB direto porta 8772 — build {build}")
    print("[Nexus] Acesse: https://sistema.transporteexecutivo.com/")
    print("[Nexus] NAO use /vnc.html — se aparecer noVNC, apague NEXUS_SISTEMA_UI=vnc e rebuild.")
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
        _verify_sistema_bundle()
        _run_sistema()
    print("[Nexus] docker_entrypoint modo motor")
    print("[Nexus] Iniciando Motor de Reservas (uvicorn)")
    _run_motor()


if __name__ == "__main__":
    main()
