"""Importa app_state.json, settings e automations para Supabase."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.repository.supabase_client import is_configured
from app.repository.supabase_store import import_json_file, count_all_collections
from app.settings_store import load_settings, save_settings, SETTINGS_FILE, DEFAULT_SETTINGS
from app.automations import save_automations, AUTOMATIONS_FILE, _normalize_automation


def main():
    if not is_configured():
        print("FAIL: Supabase nao configurado")
        return 1

    state_path = ROOT / "data" / "app_state.json"
    with open(state_path, encoding="utf-8") as handle:
        local_counts = {k: len(v) for k, v in json.load(handle).items() if isinstance(v, list)}

    print("Importando app_state.json...")
    db_counts = import_json_file(str(state_path))

    settings_path = ROOT / "data" / "settings.json"
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as handle:
            settings = json.load(handle)
        save_settings({**DEFAULT_SETTINGS, **settings})
        print("Settings importados.")

    automations_path = ROOT / "data" / "automations.json"
    if automations_path.exists():
        with open(automations_path, encoding="utf-8") as handle:
            loaded = json.load(handle)
        class _App:
            automations = [_normalize_automation(x) for x in loaded if _normalize_automation(x)]
        save_automations(_App())
        print("Automations importados.")

    print("\n=== VALIDACAO ===")
    mismatches = []
    for key, local in local_counts.items():
        if key in {"rede_empresas", "coverage"}:
            continue
        remote = db_counts.get(key, 0)
        if key == "rede_empresas":
            remote = db_counts.get("partner_networks", 0)
        status = "OK" if remote >= local else "DIVERGE"
        if status == "DIVERGE":
            mismatches.append((key, local, remote))
        print(f"{key}: local={local} supabase={remote} [{status}]")

    if mismatches:
        print("\nDIVERGENCIAS:", mismatches)
        return 1
    print("\nIMPORT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
