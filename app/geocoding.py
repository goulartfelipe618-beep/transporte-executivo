"""Geocodificacao headless — sem Tkinter (Docker / Master Web)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

GEOCODE_CACHE = Path("data") / "geocode_cache.json"

CITY_COORDS = {
    "florianopolis": (-27.5954, -48.548),
    "balneario camboriu": (-26.9906, -48.6346),
    "balneário camboriú": (-26.9906, -48.6346),
    "sao paulo": (-23.5505, -46.6333),
    "rio de janeiro": (-22.9068, -43.1729),
    "curitiba": (-25.4284, -49.2733),
    "porto alegre": (-30.0346, -51.2177),
    "brasilia": (-15.7939, -47.8828),
    "belo horizonte": (-19.9167, -43.9345),
}


def extract_city(value):
    text = str(value or "").strip()
    if not text:
        return "Sem cidade"
    if "/" in text:
        text = text.split("/", 1)[0].strip()
    if "," in text:
        text = text.split(",")[-1].strip()
    return text or "Sem cidade"


def _load_cache():
    if not GEOCODE_CACHE.is_file():
        return {}
    try:
        return json.loads(GEOCODE_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache):
    GEOCODE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    GEOCODE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def geocode_address(address):
    key = address.strip().lower()
    cache = _load_cache()
    if key in cache:
        item = cache[key]
        return item.get("lat"), item.get("lng"), item.get("source", "cache")

    city_key = extract_city(address).lower()
    if city_key in CITY_COORDS:
        lat, lng = CITY_COORDS[city_key]
        cache[key] = {"lat": lat, "lng": lng, "source": "cidade"}
        _save_cache(cache)
        return lat, lng, "cidade"

    try:
        query = urllib.parse.quote(f"{address}, Brasil")
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
        request = urllib.request.Request(url, headers={"User-Agent": "NexusTransfer/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload:
            lat = float(payload[0]["lat"])
            lng = float(payload[0]["lon"])
            cache[key] = {"lat": lat, "lng": lng, "source": "openstreetmap"}
            _save_cache(cache)
            return lat, lng, "openstreetmap"
    except Exception:
        pass

    return None, None, "nao encontrado"
