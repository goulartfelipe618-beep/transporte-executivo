"""Complementos da pagina Metricas — read-only, sem alterar metrics_service."""
from __future__ import annotations

from .metrics_service import build_metrics_stats, money_display


STATUS_BAR_COLORS = {
    "Pendentes": "#d97706",
    "Confirmadas": "#2563eb",
    "Concluidas": "#16a34a",
    "Canceladas": "#dc2626",
}


def metrics_reservations(app):
    items = getattr(app, "reservations", []) or []
    return [item for item in items if isinstance(item, dict)]


def latest_reservations(reservations, *, limit=5):
    rows = []
    for item in list(reservations or [])[:limit]:
        numero = str(item.get("numero", ""))
        slug = numero.replace("#", "")
        rows.append(
            {
                "numero": numero,
                "cliente": item.get("cliente", ""),
                "trajeto": item.get("trajeto", ""),
                "valor": item.get("valor", "R$ 0,00"),
                "status": item.get("status", ""),
                "href": f"/reservas/{slug}" if slug else "",
            }
        )
    return rows


def status_bars(statuses):
    total = max(sum(statuses.values()), 1)
    bars = []
    for label, value in statuses.items():
        bars.append(
            {
                "label": label,
                "value": value,
                "width_pct": max(int((value / total) * 100), 4 if value else 0),
                "color": STATUS_BAR_COLORS.get(label, "#2563eb"),
            }
        )
    return bars


def route_bars(routes):
    if not routes:
        return []
    max_count = max(count for _, count in routes)
    bars = []
    for index, (route, count) in enumerate(routes, start=1):
        bars.append(
            {
                "rank": index,
                "route": route,
                "count": count,
                "width_pct": max(int((count / max_count) * 100), 8 if count else 0),
            }
        )
    return bars


def monthly_chart_bars(monthly):
    max_count = max([item.get("count", 0) for item in monthly] + [1])
    bars = []
    for item in monthly:
        count = item.get("count", 0)
        bars.append(
            {
                "label": item.get("label", ""),
                "year": item.get("year", ""),
                "count": count,
                "revenue_display": item.get("revenue_display", money_display(0)),
                "height_pct": max(int((count / max_count) * 100), 4 if count else 0),
            }
        )
    return bars


def metrics_page_context(reservations):
    reservations = [item for item in reservations if isinstance(item, dict)]
    stats = build_metrics_stats(reservations)
    return {
        "stats": stats,
        "latest": latest_reservations(reservations),
        "status_bars": status_bars(stats["statuses"]),
        "route_bars": route_bars(stats["routes"]),
        "monthly_bars": monthly_chart_bars(stats["monthly"]),
    }
