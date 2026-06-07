"""Protege o codigo contra reversao acidental. Snapshot segue o disco (versao mais nova)."""
import hashlib
import json
import os
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_DIR = os.path.join(ROOT, "data", "code_snapshot")
MANIFEST_FILE = os.path.join(ROOT, "data", "code_manifest.json")

# Arquivo existe + marcador obrigatorio. Hash NAO dispara restore (evita reverter edicoes novas).
PROTECTED_FILES = {
    "main.py": "code_guard",
    ".cursor/rules/version-integrity.mdc": "Versao Mais Nova Obrigatoria",
    "app/version.py": "APP_BUILD",
    "app/main_window.py": "APP_BUILD",
    "app/components.py": "setup_placeholder",
    "app/theme.py": "styled_button",
    "app/ibge.py": "get_states",
    "app/geography.py": "operational_points",
    "app/coverage_ui.py": "render_abrangencia",
    "app/full_features.py": "render_settings",
    "app/code_guard.py": "ensure_code_integrity",
    "app/storage.py": "load_state",
    "app/settings_store.py": "DEFAULT_SETTINGS",
    "app/portal_server.py": "start_driver_portal_server",
    "app/portal_auth.py": "ensure_portal_security",
    "app/company_portal.py": "start_company_portal_server",
    "app/automations.py": "AUTOMACAO SOLICITACAO PARA SER MOTORISTA",
    "app/reservations.py": "download_reservation",
    "app/pages.py": "render_finance",
    "app/sidebar.py": "FINANCEIRO",
    "app/data.py": "INITIAL_RESERVATIONS = []",
    "app/utils.py": "reopen_window",
    "app/vehicles_model.py": "VEHICLE_TYPES",
    "app/pricing_engine.py": "list_pricing_sources",
    "app/partner_network_vehicles.py": "network_vehicles_for_partner",
    "app/repository/supabase_store.py": "persist_state",
    "app/repository/supabase_mappers.py": "TO_ROW",
    "app/bind_host.py": "bind_host",
    "app/production_runtime.py": "bootstrap_production_services",
    "app/partner_network_reservations.py": "register_network_reservation",
}

# Copiados no snapshot sem checagem de marcador (modulos novos / integracao).
SNAPSHOT_EXTRA_PATHS = (
    "app/repository/supabase_client.py",
    "app/repository/supabase_config.py",
    "app/repository/supabase_repository.py",
    "app/repository/app_repository.py",
    "app/partner_network_reservations.py",
    "app/partner_network_gateway.py",
    "scripts/validate_supabase_production.py",
    "scripts/run_production_server.py",
    "requirements.txt",
    "INICIAR_VPS.bat",
    "Dockerfile",
    "Dockerfile.sistema",
    "docker-compose.yml",
    "docker-compose.sistema.yml",
    ".env.motor.example",
    ".env.sistema.example",
    "DEPLOY_EASYPANEL.md",
    "app/middleware/trusted_host.py",
)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _marker_ok(rel_path, marker):
    path = os.path.join(ROOT, rel_path)
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            return marker in handle.read()
    except OSError:
        return False


def _copy_to_snapshot(rel_path):
    src = os.path.join(ROOT, rel_path)
    if not os.path.exists(src):
        return False
    dest = os.path.join(SNAPSHOT_DIR, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)
    return True


def save_code_snapshot():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    manifest = {"saved_at": datetime.now().isoformat(), "files": {}}
    all_paths = set(PROTECTED_FILES) | set(SNAPSHOT_EXTRA_PATHS)
    for rel_path in sorted(all_paths):
        src = os.path.join(ROOT, rel_path)
        if not os.path.exists(src):
            continue
        _copy_to_snapshot(rel_path)
        entry = {"sha256": _sha256(src)}
        if rel_path in PROTECTED_FILES:
            entry["marker"] = PROTECTED_FILES[rel_path]
        manifest["files"][rel_path] = entry
    with open(MANIFEST_FILE, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)


def _load_manifest():
    if not os.path.exists(MANIFEST_FILE):
        return {}
    try:
        with open(MANIFEST_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}


def restore_file(rel_path):
    snap = os.path.join(SNAPSHOT_DIR, rel_path)
    if not os.path.exists(snap):
        return False
    dest = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(snap, dest)
    return True


def restore_code_snapshot():
    restored = []
    for rel_path in PROTECTED_FILES:
        if restore_file(rel_path):
            restored.append(rel_path)
    for rel_path in SNAPSHOT_EXTRA_PATHS:
        if restore_file(rel_path):
            restored.append(rel_path)
    return restored


def ensure_code_integrity(auto_restore=True):
    """
    Restaura SOMENTE arquivos ausentes ou sem marcador (corrupcao real).
    Divergencia de hash com marcador valido = disco e mais novo; atualiza snapshot.
    """
    broken = [rel for rel, marker in PROTECTED_FILES.items() if not _marker_ok(rel, marker)]
    if broken and auto_restore and os.path.isdir(SNAPSHOT_DIR):
        for rel in broken:
            restore_file(rel)
        broken = [rel for rel, marker in PROTECTED_FILES.items() if not _marker_ok(rel, marker)]
    if broken:
        return False, broken
    save_code_snapshot()
    return True, []


def sync_snapshot_from_disk():
    """Atualiza snapshot com o codigo atual (chamar apos edicoes validadas)."""
    save_code_snapshot()
