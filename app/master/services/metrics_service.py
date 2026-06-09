"""Metricas do dashboard — extraidas de pages.py."""
from __future__ import annotations

from datetime import date, datetime

MONTH_NAMES = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def parse_money_value(value):
    text = str(value or "0").replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def money_display(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_reservation_date(reservation):
    value = reservation if isinstance(reservation, str) else reservation.get("data", "")
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def count_by_status(reservations, status):
    return sum(1 for item in reservations if item.get("status") == status)


def monthly_summary(reservations):
    today = date.today()
    months = []
    for offset in range(5, -1, -1):
        month = today.month - offset
        year = today.year
        while month < 1:
            month += 12
            year -= 1
        months.append({"month": month, "year": year, "label": MONTH_NAMES[month][:3], "count": 0, "revenue": 0, "revenue_display": money_display(0)})
    for reservation in reservations:
        reservation_date = parse_reservation_date(reservation)
        if not reservation_date:
            continue
        for item in months:
            if item["month"] == reservation_date.month and item["year"] == reservation_date.year:
                item["count"] += 1
                item["revenue"] += parse_money_value(reservation.get("valor", ""))
    for item in months:
        item["revenue_display"] = money_display(item["revenue"])
    return months


def top_routes(reservations):
    counts = {}
    for reservation in reservations:
        route = reservation.get("trajeto") or "Sem trajeto"
        counts[route] = counts.get(route, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]


def build_metrics_stats(reservations):
    reservations = [item for item in reservations if isinstance(item, dict)]
    total = len(reservations)
    revenue = sum(parse_money_value(item.get("valor", "")) for item in reservations)
    done = count_by_status(reservations, "Concluida")
    pending = count_by_status(reservations, "Pendente")
    ticket = revenue / total if total else 0
    return {
        "total": total,
        "revenue": revenue,
        "revenue_display": money_display(revenue),
        "ticket": ticket,
        "ticket_display": money_display(ticket),
        "done": done,
        "done_pct": int((done / total) * 100) if total else 0,
        "pending": pending,
        "monthly": monthly_summary(reservations),
        "statuses": {
            "Pendentes": pending,
            "Confirmadas": count_by_status(reservations, "Confirmada"),
            "Concluidas": done,
            "Canceladas": count_by_status(reservations, "Cancelada"),
        },
        "routes": top_routes(reservations),
    }
