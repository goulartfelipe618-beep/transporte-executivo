"""Runtime de producao sem Tkinter — motor de reservas + portais + gateway."""
from __future__ import annotations

import signal
import sys
import threading
import time

from .api_gateway import start_api_gateway_server
from .automations import ensure_automations_loaded, start_automation_webhook_server
from .company_portal import start_company_portal_server
from .operational_network import ensure_operational_network
from .partner_network import ensure_partner_networks
from .portal_auth import ensure_portal_security
from .portal_server import start_driver_portal_server
from .portal_urls import company_portal_base, driver_portal_base, engine_base, sistema_web_base
from .repository import AppRepository
from .sistema_web import start_sistema_web_server
from .version import APP_BUILD


class RuntimeApp:
    """App em memoria carregado do Supabase (sem UI desktop)."""

    def __init__(self):
        self.repo = AppRepository.bootstrap(self)

    def save_state(self):
        self.repo.persist()


def bootstrap_production_services(app):
    ensure_automations_loaded(app)
    _, network_changed = ensure_operational_network(app)
    portal_changed = ensure_portal_security(app)
    rede_changed = ensure_partner_networks(app)
    if network_changed or portal_changed or rede_changed:
        app.save_state()
    start_automation_webhook_server(app)
    gateway_url = start_api_gateway_server(app)
    start_driver_portal_server(app)
    start_company_portal_server(app)
    start_sistema_web_server(app)
    return gateway_url


def run_production_forever():
    print(f"[Nexus] Runtime producao build {APP_BUILD}")
    app = RuntimeApp()
    gateway_url = bootstrap_production_services(app)
    if not gateway_url:
        print("[Nexus] ERRO: gateway nao iniciou. Verifique porta 8770.")
        sys.exit(1)
    print(f"[Nexus] API gateway: {gateway_url}")
    print(f"[Nexus] Sistema web: {sistema_web_base()}")
    print(f"[Nexus] Portal motorista: {driver_portal_base()}")
    print(f"[Nexus] Portal empresa: {company_portal_base()}")
    print(f"[Nexus] Motor rede (engine): {engine_base()}/{{slug}}/{{codigo}}")
    print("[Nexus] Servicos ativos. Ctrl+C para encerrar.")

    stop = threading.Event()

    def _shutdown(*_args):
        stop.set()

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    while not stop.is_set():
        time.sleep(1)
