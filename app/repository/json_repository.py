"""Repositorio JSON — fonte atual de persistencia (app_state.json)."""
from __future__ import annotations

from typing import Callable, Optional


class JsonListRepository:
    """CRUD sobre uma lista em memoria ligada ao app; persistencia via save_state."""

    def __init__(self, app, collection_key: str, *, id_field: str = "id"):
        self._app = app
        self._key = collection_key
        self._id_field = id_field

    @property
    def items(self):
        return getattr(self._app, self._key)

    def all(self):
        return list(self.items)

    def count(self):
        return len(self.items)

    def find_by_id(self, entity_id):
        entity_id = str(entity_id or "")
        for item in self.items:
            if str(item.get(self._id_field, "")) == entity_id:
                return item
        return None

    def find_one(self, predicate: Callable) -> Optional[dict]:
        for item in self.items:
            if predicate(item):
                return item
        return None

    def find_many(self, predicate: Callable) -> list:
        return [item for item in self.items if predicate(item)]

    def insert(self, item, index=0):
        self.items.insert(index, item)
        return item

    def append(self, item):
        self.items.append(item)
        return item

    def update(self, entity_id, patch: dict):
        entity_id = str(entity_id or "")
        for index, item in enumerate(self.items):
            if str(item.get(self._id_field, "")) == entity_id:
                updated = {**item, **patch}
                self.items[index] = updated
                return updated
        return None

    def replace(self, entity_id, item: dict):
        entity_id = str(entity_id or "")
        for index, row in enumerate(self.items):
            if str(row.get(self._id_field, "")) == entity_id:
                self.items[index] = item
                return item
        return None

    def delete(self, entity_id):
        entity_id = str(entity_id or "")
        kept = [item for item in self.items if str(item.get(self._id_field, "")) != entity_id]
        if len(kept) == len(self.items):
            return False
        setattr(self._app, self._key, kept)
        return True

    def replace_all(self, items):
        setattr(self._app, self._key, list(items))

    def persist(self):
        if hasattr(self._app, "save_state"):
            self._app.save_state()
