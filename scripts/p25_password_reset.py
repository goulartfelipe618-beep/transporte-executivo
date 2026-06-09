"""P2.5 — Reset controlado de senha via update_user (Master Web equivalente)."""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")

from app.master.services.company_user_service import generate_temporary_password, update_user
from app.storage import load_state


def main():
    state = load_state()
    app = SimpleNamespace(**state)
    for key in state:
        if not key.startswith("_"):
            setattr(app, key, state[key])

    company_id = "emp-000001"
    user_id = "usr-001"
    company = next(c for c in app.clients if c.get("id") == company_id)
    user = next(u for u in (company.get("usuarios") or []) if u.get("id") == user_id)

    new_password = generate_temporary_password(14)
    form_data = {
        "nome": user.get("nome", ""),
        "email": user.get("email", ""),
        "telefone": user.get("telefone", ""),
        "perfil": user.get("perfil", "Administrador da Empresa"),
        "status": user.get("status", "Ativo"),
        "senha": new_password,
        "must_change_password": "false",
    }

    update_user(
        app,
        company_id,
        user_id,
        form_data,
        actor={"id": "master-admin", "nome": "Admin Master"},
    )

    result = {
        "usuario": user_id,
        "email": user.get("email"),
        "metodo": "company_user_service.update_user (POST Master /empresas/{id}/usuarios/{id}/editar)",
        "must_change_password": False,
        "ok": True,
    }
    print(json.dumps(result, ensure_ascii=False))
    print("P25_PASSWORD_SET")
    # Senha emitida apenas em stdout desta execucao para homologacao imediata.
    print("P25_PASSWORD_VALUE", new_password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
