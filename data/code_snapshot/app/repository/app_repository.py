"""Facade de repositorios — ponto unico para UI e servicos."""
from __future__ import annotations

from ..storage import STATE_KEYS, load_state, save_state
from .ids import ensure_entity_ids
from .json_repository import JsonListRepository
from .supabase_client import is_configured
from .supabase_repository import SupabaseListRepository


class AppRepository:
    """
    UI -> AppRepository -> SupabaseRepository (primario) + JSON backup.
    """

    BACKEND = "supabase" if is_configured() else "json"

    def __init__(self, app):
        self.app = app
        repo_cls = SupabaseListRepository if self.BACKEND == "supabase" else JsonListRepository
        self.reservations = repo_cls(app, "reservations")
        self.clients = repo_cls(app, "clients")
        self.drivers = repo_cls(app, "drivers")
        self.vehicles = repo_cls(app, "vehicles")
        self.operational_points = repo_cls(app, "operational_points")
        self.hotels = repo_cls(app, "hotels")
        self.airports = repo_cls(app, "airports")
        self.networks = repo_cls(app, "networks")
        self.transport_requests = repo_cls(app, "transport_requests")
        self.company_leads = repo_cls(app, "company_leads")
        self.driver_leads = repo_cls(app, "driver_leads")
        self.event_log = repo_cls(app, "event_log")
        self.portal_sessions = repo_cls(app, "portal_sessions")

    @classmethod
    def bootstrap(cls, app):
        state = load_state()
        for key in STATE_KEYS:
            setattr(app, key, list(state.get(key, [])))
        repo = cls(app)
        if ensure_entity_ids(app):
            repo.persist()
        return repo

    def persist(self):
        save_state(self.app)

    def reservations_for_company(self, company_id):
        company_id = str(company_id or "")
        return self.reservations.find_many(lambda r: str(r.get("company_id", "")) == company_id)

    def reservations_for_driver(self, driver_id):
        driver_id = str(driver_id or "")
        return self.reservations.find_many(lambda r: str(r.get("driver_id", "")) == driver_id)

    def transport_requests_for_company(self, company_id):
        company_id = str(company_id or "")
        return self.transport_requests.find_many(lambda r: str(r.get("company_id", "")) == company_id)

    def find_company(self, company_id):
        return self.clients.find_by_id(company_id)

    def find_driver(self, driver_id):
        return self.drivers.find_by_id(driver_id)

    def find_reservation(self, reservation_id):
        return self.reservations.find_by_id(reservation_id)
