"""Validacao local P2.1 — compatibilidade driver_id legacy vs UUID Supabase."""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from app.portal_auth import driver_reservations_for, reservation_belongs_to_driver


class _App:
    reservations = [
        {"id": "r1", "driver_id": "drv-0001"},
        {"id": "r2", "driver_id": "uuid-supabase-abc"},
        {"id": "r3", "driver_uuid": "uuid-supabase-abc"},
        {"id": "r4", "driver_id": "other"},
    ]


def main() -> int:
    app = _App()
    driver_legacy = {"id": "drv-0001"}
    driver_uuid = {"id": "drv-0001", "supabase_id": "uuid-supabase-abc"}

    legacy_ids = {r["id"] for r in driver_reservations_for(app, driver_legacy)}
    assert legacy_ids == {"r1"}, legacy_ids

    uuid_ids = {r["id"] for r in driver_reservations_for(app, driver_uuid)}
    assert uuid_ids == {"r1", "r2", "r3"}, uuid_ids

    assert reservation_belongs_to_driver({"driver_id": "uuid-supabase-abc"}, driver_uuid)
    assert reservation_belongs_to_driver({"driver_uuid": "uuid-supabase-abc"}, driver_uuid)
    assert not reservation_belongs_to_driver({"driver_id": "other"}, driver_uuid)

    print("P21_DRIVER_IDENTITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
