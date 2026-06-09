"""Agenda — calendario mensal de reservas (read-only, sem Tkinter)."""
from __future__ import annotations

import calendar
from datetime import date, datetime

MONTH_NAMES = [
    "",
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

WEEKDAY_NAMES = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"]

MAX_CHIPS_PER_DAY = 3


def parse_reservation_date(reservation):
    value = reservation if isinstance(reservation, str) else reservation.get("data", "")
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(str(value or "").strip(), fmt).date()
        except ValueError:
            pass
    return None


def extract_hour(value):
    text = str(value or "")
    if " " not in text:
        return ""
    return text.split(" ", 1)[1][:5]


def reservation_chip_text(reservation):
    number = reservation.get("numero", "")
    kind = reservation.get("tipo", "Transfer")
    client = reservation.get("cliente", "")
    hour = reservation.get("hora") or extract_hour(reservation.get("data", ""))
    if kind == "Ida" or "Somente Ida" in str(kind):
        short_kind = "IDA"
    elif kind == "Volta":
        short_kind = "VOLTA"
    else:
        short_kind = str(kind)[:6].upper()
    suffix = f" - {hour}" if hour else ""
    return f"{number}  {short_kind}  {str(client)[:18]}{suffix}"


def group_reservations_by_day(reservations):
    grouped = {}
    for reservation in reservations or []:
        if not isinstance(reservation, dict):
            continue
        reservation_date = parse_reservation_date(reservation)
        if not reservation_date:
            continue
        grouped.setdefault(reservation_date, []).append(reservation)
    return grouped


def normalize_month_year(year, month):
    today = date.today()
    try:
        year = int(year) if year is not None else today.year
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(month) if month is not None else today.month
    except (TypeError, ValueError):
        month = today.month
    if month < 1:
        month = 1
    if month > 12:
        month = 12
    return year, month


def month_navigation(year, month, delta):
    month_index = int(month) + int(delta)
    nav_year = int(year)
    if month_index < 1:
        month_index = 12
        nav_year -= 1
    elif month_index > 12:
        month_index = 1
        nav_year += 1
    return nav_year, month_index


def month_metrics(reservations, year, month):
    total = 0
    for item in reservations or []:
        reservation_date = parse_reservation_date(item)
        if reservation_date and reservation_date.month == month and reservation_date.year == year:
            total += 1
    return {"total_month": total}


def _reservation_chip(reservation):
    numero = str(reservation.get("numero", "")).strip()
    return {
        "numero": numero,
        "label": reservation_chip_text(reservation).upper(),
        "href": f"/reservas/{numero}" if numero else "#",
    }


def build_month_calendar(reservations, year, month):
    year, month = normalize_month_year(year, month)
    active_month = date(year, month, 1)
    today = date.today()
    grouped = group_reservations_by_day(reservations)
    metrics = month_metrics(reservations, year, month)
    prev_year, prev_month = month_navigation(year, month, -1)
    next_year, next_month = month_navigation(year, month, 1)

    weeks = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(year, month):
        week_rows = []
        for day in week:
            day_reservations = grouped.get(day, [])
            chips = [_reservation_chip(item) for item in day_reservations[:MAX_CHIPS_PER_DAY]]
            overflow = max(0, len(day_reservations) - MAX_CHIPS_PER_DAY)
            week_rows.append(
                {
                    "date": day.isoformat(),
                    "day": day.day,
                    "is_current_month": day.month == month,
                    "is_today": day == today,
                    "count": len(day_reservations),
                    "chips": chips,
                    "overflow": overflow,
                    "overflow_label": f"+ {overflow} RESERVAS" if overflow else "",
                }
            )
        weeks.append(week_rows)

    return {
        "year": year,
        "month": month,
        "month_label": f"{MONTH_NAMES[month].upper()} · {year}",
        "weekday_names": WEEKDAY_NAMES,
        "weeks": weeks,
        "prev": {"year": prev_year, "month": prev_month},
        "next": {"year": next_year, "month": next_month},
        "today": {"year": today.year, "month": today.month},
        "metrics": metrics,
    }
