"""Camada de persistencia — JsonRepository hoje, SupabaseRepository futuro."""
from .app_repository import AppRepository
from .ids import ENTITY_PREFIXES, ensure_entity_ids, next_entity_id
from .json_repository import JsonListRepository

__all__ = [
    "AppRepository",
    "JsonListRepository",
    "ENTITY_PREFIXES",
    "ensure_entity_ids",
    "next_entity_id",
]
