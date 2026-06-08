"""Sistema Master real (Tkinter) no browser via Xvfb + noVNC — porta 8772."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPLAY = os.environ.get("NEXUS_DISPLAY", ":99")
VNC_PORT = int(os.environ.get("NEXUS_VNC_PORT", "5900"))
WEB_PORT = int(os.environ.get("NEXUS_NOVNC_PORT", "8772"))
SCREEN = os.environ.get("NEXUS_VNC_SCREEN", "1440x900x24")

PROCS: list[subprocess.Popen] = []


def _which(name):
    return shutil.which(name)


def _spawn(cmd, *, env=None, name=""):
    print(f"[Nexus] Iniciando {name or cmd[0]}: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env or os.environ.copy())
    PROCS.append(proc)
    return proc


def _shutdown(*_args):
    print("[Nexus] Encerrando servicos VNC/GUI...")
    for proc in reversed(PROCS):
        if proc.poll() is None:
            proc.terminate()
    time.sleep(0.5)
    for proc in reversed(PROCS):
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)


def _wait_display(timeout=15):
    display_num = DISPLAY.lstrip(":")
    for _ in range(timeout * 4):
        try:
            result = subprocess.run(
                ["xdpyinfo", "-display", DISPLAY],
                capture_output=True,
                timeout=3,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        if Path(f"/tmp/.X{display_num}-lock").exists():
            return True
        time.sleep(0.25)
    return False


def main():
    os.chdir(ROOT)
    os.environ["DISPLAY"] = DISPLAY
    os.environ["NEXUS_SKIP_SISTEMA_WEB"] = "1"

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    xvfb = _which("Xvfb")
    x11vnc = _which("x11vnc")
    websockify = _which("websockify")
    if not xvfb or not x11vnc or not websockify:
        print("[Nexus] ERRO: instale xvfb, x11vnc e websockify na imagem Docker.")
        sys.exit(1)

    novnc_web = "/usr/share/novnc"
    if not Path(novnc_web).is_dir():
        novnc_web = str(ROOT / "static" / "novnc")

    env = os.environ.copy()
    env["NEXUS_SKIP_SISTEMA_WEB"] = "1"
    _spawn([sys.executable, "scripts/run_production_server.py"], env=env, name="headless API/portais")

    _spawn([xvfb, DISPLAY, "-screen", "0", SCREEN, "-ac", "-nolisten", "tcp"], name="Xvfb")
    time.sleep(1.5)
    if not _wait_display():
        print(f"[Nexus] AVISO: display {DISPLAY} pode nao estar pronto; continuando...")

    _spawn(
        [
            x11vnc,
            "-display",
            DISPLAY,
            "-forever",
            "-shared",
            "-nopw",
            "-localhost",
            "-rfbport",
            str(VNC_PORT),
            "-noxdamage",
        ],
        name="x11vnc",
    )
    time.sleep(0.5)

    bind_host = os.environ.get("NEXUS_BIND_HOST", "0.0.0.0")
    _spawn(
        [
            websockify,
            f"--web={novnc_web}",
            f"{bind_host}:{WEB_PORT}",
            f"127.0.0.1:{VNC_PORT}",
        ],
        name="noVNC",
    )

    print(f"[Nexus] GUI Tkinter disponivel em noVNC porta {WEB_PORT}")
    print(f"[Nexus] Abra /vnc.html?autoconnect=1&resize=scale&reconnect=1")
    print("[Nexus] Iniciando main.py (TransferSystemApp)...")

    os.execvp(sys.executable, [sys.executable, "main.py"])


if __name__ == "__main__":
    main()
