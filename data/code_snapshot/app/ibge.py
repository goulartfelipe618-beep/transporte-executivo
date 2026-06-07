"""Integracao com a API oficial do IBGE para estados e municipios."""
import gzip
import json
import os
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(ROOT, "data", "ibge_cache.json")
CACHE_TTL_DAYS = 30

IBGE_STATES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"
IBGE_MUNICIPALITIES_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios?orderBy=nome"
)

FALLBACK_STATES = [
    {"id": 12, "sigla": "AC", "nome": "Acre"},
    {"id": 27, "sigla": "AL", "nome": "Alagoas"},
    {"id": 16, "sigla": "AP", "nome": "Amapa"},
    {"id": 13, "sigla": "AM", "nome": "Amazonas"},
    {"id": 29, "sigla": "BA", "nome": "Bahia"},
    {"id": 23, "sigla": "CE", "nome": "Ceara"},
    {"id": 53, "sigla": "DF", "nome": "Distrito Federal"},
    {"id": 32, "sigla": "ES", "nome": "Espirito Santo"},
    {"id": 52, "sigla": "GO", "nome": "Goias"},
    {"id": 21, "sigla": "MA", "nome": "Maranhao"},
    {"id": 51, "sigla": "MT", "nome": "Mato Grosso"},
    {"id": 50, "sigla": "MS", "nome": "Mato Grosso do Sul"},
    {"id": 31, "sigla": "MG", "nome": "Minas Gerais"},
    {"id": 15, "sigla": "PA", "nome": "Para"},
    {"id": 25, "sigla": "PB", "nome": "Paraiba"},
    {"id": 41, "sigla": "PR", "nome": "Parana"},
    {"id": 26, "sigla": "PE", "nome": "Pernambuco"},
    {"id": 22, "sigla": "PI", "nome": "Piaui"},
    {"id": 33, "sigla": "RJ", "nome": "Rio de Janeiro"},
    {"id": 24, "sigla": "RN", "nome": "Rio Grande do Norte"},
    {"id": 43, "sigla": "RS", "nome": "Rio Grande do Sul"},
    {"id": 11, "sigla": "RO", "nome": "Rondonia"},
    {"id": 14, "sigla": "RR", "nome": "Roraima"},
    {"id": 42, "sigla": "SC", "nome": "Santa Catarina"},
    {"id": 35, "sigla": "SP", "nome": "Sao Paulo"},
    {"id": 28, "sigla": "SE", "nome": "Sergipe"},
    {"id": 17, "sigla": "TO", "nome": "Tocantins"},
]


def _fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NexusTransfer/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"states": None, "states_updated": None, "municipalities": {}}
    try:
        with open(CACHE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {"states": None, "states_updated": None, "municipalities": {}}
    data.setdefault("municipalities", {})
    return data


def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)


def _cache_is_fresh(timestamp):
    if not timestamp:
        return False
    try:
        updated = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    return datetime.now() - updated < timedelta(days=CACHE_TTL_DAYS)


def _normalize_state(raw):
    return {
        "id": int(raw["id"]),
        "sigla": str(raw.get("sigla", "")).upper(),
        "nome": str(raw.get("nome", "")).strip(),
    }


def _normalize_municipality(raw, uf):
    micro = raw.get("microrregiao") or {}
    meso = micro.get("mesorregiao") or {}
    state = meso.get("UF") or {}
    return {
        "id": int(raw["id"]),
        "nome": str(raw.get("nome", "")).strip(),
        "uf": str(state.get("sigla") or uf).upper(),
    }


def get_states(force_refresh=False):
    cache = _load_cache()
    if not force_refresh and cache.get("states") and _cache_is_fresh(cache.get("states_updated")):
        return list(cache["states"])

    try:
        payload = _fetch_json(IBGE_STATES_URL)
        states = [_normalize_state(item) for item in payload]
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        states = [_normalize_state(item) for item in FALLBACK_STATES]

    cache["states"] = states
    cache["states_updated"] = datetime.now().isoformat(timespec="seconds")
    _save_cache(cache)
    return list(states)


def get_municipalities(uf, force_refresh=False):
    uf = str(uf or "").upper()
    if not uf:
        return []

    cache = _load_cache()
    municipalities_cache = cache.setdefault("municipalities", {})
    entry = municipalities_cache.get(uf) or {}
    if not force_refresh and entry.get("items") and _cache_is_fresh(entry.get("updated")):
        return list(entry["items"])

    url = IBGE_MUNICIPALITIES_URL.format(uf=uf)
    try:
        payload = _fetch_json(url)
        municipalities = [_normalize_municipality(item, uf) for item in payload]
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        municipalities = list(entry.get("items") or [])

    municipalities_cache[uf] = {
        "updated": datetime.now().isoformat(timespec="seconds"),
        "items": municipalities,
    }
    _save_cache(cache)
    return list(municipalities)


def find_state_by_sigla(states, sigla):
    sigla = str(sigla or "").upper()
    for state in states:
        if state.get("sigla") == sigla:
            return state
    return None


def find_municipality_by_name(municipalities, name):
    target = _normalize_text(name)
    if not target:
        return None
    for municipality in municipalities:
        if _normalize_text(municipality.get("nome")) == target:
            return municipality
    for municipality in municipalities:
        if target in _normalize_text(municipality.get("nome")):
            return municipality
    return None


def _normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())
