"""Mapa de abrangencia — motoristas e clientes por endereco cadastrado."""
import json
import threading
import tkinter as tk
import urllib.parse
import urllib.request
from pathlib import Path

from .theme import COLORS, FONTS, styled_button

GEOCODE_CACHE = Path("data") / "geocode_cache.json"
MAP_HTML = Path("data") / "coverage_map.html"

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


def open_coverage_map(app):
    window = tk.Toplevel(app)
    window.title("Mapa de Abrangencia")
    window.configure(bg=COLORS["bg"])
    window.geometry("1280x760")
    window.minsize(1000, 620)
    window.transient(app)

    header = tk.Frame(window, bg=COLORS["bg"])
    header.pack(fill="x", padx=12, pady=(10, 6))
    tk.Label(header, text="Mapa de Abrangencia", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 16)).pack(side="left")
    status = tk.Label(header, text="Carregando enderecos e coordenadas...", bg=COLORS["bg"], fg=COLORS["muted"], font=FONTS["small"])
    status.pack(side="left", padx=(12, 0))

    host = tk.Frame(window, bg=COLORS["bg"])
    host.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def worker():
        markers, stats = build_markers(app)
        html_path = write_map_html(markers, stats)
        app.after(0, lambda: _show_map(host, window, status, html_path, stats))

    threading.Thread(target=worker, daemon=True).start()


def _show_map(host, window, status, html_path, stats):
    for widget in host.winfo_children():
        widget.destroy()

    summary = (
        f'Motoristas: {stats["drivers"]}  ·  Clientes: {stats["clients"]}  ·  '
        f'Pins: {stats["pins"]}  ·  Cidades: {stats["cities"]}'
    )
    status.configure(text=summary)

    try:
        from tkinterweb import HtmlFrame

        frame = HtmlFrame(host, messages_enabled=False)
        frame.load_file(str(html_path))
        frame.pack(fill="both", expand=True)
        return
    except Exception:
        pass

    panel = tk.Frame(host, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    panel.pack(fill="both", expand=True, padx=20, pady=20)
    tk.Label(
        panel,
        text="Mapa gerado com sucesso.",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=("Segoe UI Semibold", 14),
    ).pack(pady=(30, 8))
    tk.Label(
        panel,
        text=summary,
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["small"],
    ).pack(pady=(0, 16))
    tk.Label(
        panel,
        text=str(html_path),
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=FONTS["tiny"],
        wraplength=720,
    ).pack(pady=(0, 20))
    actions = tk.Frame(panel, bg=COLORS["panel"])
    actions.pack(pady=8)
    styled_button(actions, "Abrir mapa no navegador", style="primary", command=lambda: _open_in_browser(html_path)).pack(side="left", padx=6)
    styled_button(actions, "Atualizar mapa", style="secondary", command=lambda: open_coverage_map(window.winfo_toplevel())).pack(side="left", padx=6)


def _open_in_browser(html_path):
    import webbrowser

    webbrowser.open(html_path.resolve().as_uri())


def build_markers(app):
    markers = []
    for driver in getattr(app, "drivers", []):
        address = format_driver_address(driver)
        if not address:
            continue
        lat, lng, source = geocode_address(address)
        if lat is None:
            continue
        city = extract_city(driver.get("cidade") or driver.get("estado", ""))
        markers.append(
            {
                "kind": "motorista",
                "name": driver.get("nome", "Motorista"),
                "address": address,
                "city": city,
                "lat": lat,
                "lng": lng,
                "source": source,
            }
        )

    for client in getattr(app, "clients", []):
        address = format_client_address(client)
        if not address:
            continue
        lat, lng, source = geocode_address(address)
        if lat is None:
            continue
        name = client.get("nome") or client.get("razao_social") or client.get("nome_fantasia") or "Cliente"
        markers.append(
            {
                "kind": "cliente",
                "name": name,
                "address": address,
                "city": extract_city(address),
                "lat": lat,
                "lng": lng,
                "source": source,
            }
        )

    cities = sorted({item["city"] for item in markers if item.get("city")})
    stats = {
        "drivers": sum(1 for item in markers if item["kind"] == "motorista"),
        "clients": sum(1 for item in markers if item["kind"] == "cliente"),
        "pins": len(markers),
        "cities": len(cities),
    }
    return markers, stats


def format_driver_address(driver):
    parts = [
        driver.get("logradouro"),
        driver.get("numero"),
        driver.get("bairro"),
        driver.get("cidade"),
        driver.get("estado"),
        driver.get("cep"),
    ]
    cleaned = [str(part).strip() for part in parts if str(part or "").strip()]
    return ", ".join(cleaned)


def format_client_address(client):
    if client.get("endereco"):
        return str(client["endereco"]).strip()
    for item in client.get("enderecos") or []:
        if item.get("endereco"):
            return str(item["endereco"]).strip()
    parts = [client.get("endereco_sede"), client.get("cidade"), client.get("estado")]
    cleaned = [str(part).strip() for part in parts if str(part or "").strip()]
    return ", ".join(cleaned)


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


def write_map_html(markers, stats):
    MAP_HTML.parent.mkdir(parents=True, exist_ok=True)
    city_counts = {}
    for item in markers:
        city = item.get("city") or "Sem cidade"
        city_counts[city] = city_counts.get(city, 0) + 1
    city_rows = sorted(city_counts.items(), key=lambda pair: pair[1], reverse=True)
    max_count = max((count for _, count in city_rows), default=1)

    markers_json = json.dumps(markers, ensure_ascii=False)
    city_html = "".join(
        f'<div class="city-row"><span>{city}</span><div class="bar"><i style="width:{int((count/max_count)*100)}%"></i></div><strong>{count}</strong></div>'
        for city, count in city_rows
    ) or '<div class="city-row"><span>Nenhum endereco geolocalizado</span></div>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Mapa de Abrangencia</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    body {{ margin:0; font-family:Segoe UI,Arial,sans-serif; background:#0f172a; color:#e2e8f0; }}
    .layout {{ display:grid; grid-template-columns:1fr 320px; height:100vh; }}
    #map {{ width:100%; height:100vh; }}
    .side {{ background:#111827; border-left:1px solid #1f2937; padding:18px; overflow:auto; }}
    h1 {{ font-size:18px; margin:0 0 8px; }}
    .muted {{ color:#94a3b8; font-size:12px; margin-bottom:16px; }}
    .stat {{ background:#1f2937; border-radius:10px; padding:10px 12px; margin-bottom:8px; font-size:13px; }}
    .city-row {{ display:grid; grid-template-columns:1fr auto; gap:8px; align-items:center; margin:10px 0; font-size:13px; }}
    .bar {{ grid-column:1 / span 2; height:8px; background:#334155; border-radius:999px; overflow:hidden; }}
    .bar i {{ display:block; height:100%; background:#f97316; }}
  </style>
</head>
<body>
  <div class="layout">
    <div id="map"></div>
    <aside class="side">
      <h1>Mapa de Abrangencia</h1>
      <div class="muted">Motoristas e clientes cadastrados com endereco.</div>
      <div class="stat">Motoristas no mapa: {stats["drivers"]}</div>
      <div class="stat">Clientes no mapa: {stats["clients"]}</div>
      <div class="stat">Pins totais: {stats["pins"]}</div>
      <div class="stat">Cidades: {stats["cities"]}</div>
      <h2 style="font-size:14px;margin-top:18px;">Por cidade</h2>
      {city_html}
    </aside>
  </div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const markers = {markers_json};
    const map = L.map('map').setView([-14.235, -51.925], 4);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap'
    }}).addTo(map);
    const bounds = [];
    markers.forEach(item => {{
      const color = item.kind === 'motorista' ? '#2563eb' : '#16a34a';
      const marker = L.circleMarker([item.lat, item.lng], {{ radius: 8, color, fillColor: color, fillOpacity: 0.85 }});
      marker.bindPopup(`<strong>${{item.name}}</strong><br>${{item.kind.toUpperCase()}}<br>${{item.address}}`);
      marker.addTo(map);
      bounds.push([item.lat, item.lng]);
    }});
    if (bounds.length) map.fitBounds(bounds, {{ padding: [40, 40] }});
  </script>
</body>
</html>"""
    MAP_HTML.write_text(html, encoding="utf-8")
    return MAP_HTML
