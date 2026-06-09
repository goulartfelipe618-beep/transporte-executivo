"""Financeiro — visao derivada de reservas (read-only, logica extraida de pages.py)."""
from __future__ import annotations

from app.domain.formatters import money_display, parse_money_value


def count_by_status(reservations, status):
    return sum(1 for item in reservations if item.get("status") == status)


def build_finance_summary(reservations):
    reservations = list(reservations or [])
    active = [item for item in reservations if item.get("status") != "Cancelada"]
    entries = []
    payables = []
    receivables = []

    for reservation in active:
        value = parse_money_value(reservation.get("valor"))
        repasse = parse_money_value(reservation.get("repasse"))
        status = reservation.get("status") or "Pendente"
        received = status == "Concluida"
        number = reservation.get("numero", "")
        date_label = reservation.get("data") or "-"

        entries.append(
            {
                "date": date_label,
                "type": "Entrada",
                "description": f"Receita transfer {number} - {reservation.get('cliente', '')}",
                "category": "Receita de transfer",
                "value": value,
                "status": "Recebido" if received else "Previsto",
            }
        )
        if not received:
            receivables.append(
                {
                    "date": date_label,
                    "client": reservation.get("cliente", ""),
                    "number": number,
                    "route": reservation.get("trajeto", ""),
                    "value": value,
                    "status": status,
                }
            )
        if repasse > 0:
            account = reservation.get("conta_pagar") or f"CP-REPASSE-{str(number).replace('#', '')}"
            account_label = reservation.get("conta_pagar_descricao") or (
                f"Repasse motorista — {reservation.get('motorista', '-')}"
            )
            entries.append(
                {
                    "date": date_label,
                    "type": "Saida",
                    "description": f"{account} — {account_label}",
                    "category": "Repasse motorista",
                    "value": repasse,
                    "status": "Pago" if received else "A pagar",
                }
            )
            payables.append(
                {
                    "date": date_label,
                    "driver": reservation.get("motorista", "-"),
                    "number": number,
                    "account": account,
                    "description": account_label,
                    "value": repasse,
                    "status": "Pago" if received else "A pagar",
                }
            )

    gross_revenue = sum(parse_money_value(item.get("valor")) for item in active)
    received_total = sum(parse_money_value(item.get("valor")) for item in active if item.get("status") == "Concluida")
    total_repasse = sum(parse_money_value(item.get("repasse")) for item in active)
    to_pay = sum(item["value"] for item in payables if item["status"] == "A pagar")
    to_receive = sum(item["value"] for item in receivables)
    net_result = gross_revenue - total_repasse
    count = len(active)

    return {
        "reservation_count": count,
        "gross_revenue": gross_revenue,
        "received": received_total,
        "to_receive": to_receive,
        "to_pay": to_pay,
        "total_repasse": total_repasse,
        "net_result": net_result,
        "average_ticket": gross_revenue / count if count else 0,
        "margin_pct": round((net_result / gross_revenue) * 100, 1) if gross_revenue else 0,
        "entries": entries,
        "payables": payables,
        "receivables": receivables,
        "status_counts": {
            "Pendentes": count_by_status(active, "Pendente"),
            "Confirmadas": count_by_status(active, "Confirmada"),
            "Concluidas": count_by_status(active, "Concluida"),
            "Canceladas": count_by_status(reservations, "Cancelada"),
        },
    }


FLOW_BAR_COLORS = {
    "primary": "#2563eb",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "accent": "#0f766e",
}


def finance_flow_bars(summary):
    items = [
        ("Receita prevista", summary["gross_revenue"], "primary"),
        ("Recebido", summary["received"], "success"),
        ("A receber", summary["to_receive"], "warning"),
        ("A pagar", summary["to_pay"], "danger"),
        ("Resultado", summary["net_result"], "accent"),
    ]
    max_value = max([abs(value) for _, value, _ in items] + [1.0])
    bars = []
    for label, value, tone in items:
        width = max(int((abs(value) / max_value) * 100), 4 if value else 0)
        bars.append(
            {
                "label": label,
                "value": value,
                "display": money_display(value),
                "width_pct": width,
                "tone": tone,
                "color": FLOW_BAR_COLORS.get(tone, FLOW_BAR_COLORS["primary"]),
            }
        )
    return bars


def finance_health_items(summary):
    margin_tone = "success" if summary["margin_pct"] >= 0 else "danger"
    return [
        {"label": "Margem", "value": f"{summary['margin_pct']}%", "tone": margin_tone},
        {"label": "Ticket medio", "value": money_display(summary["average_ticket"]), "tone": "primary"},
        {"label": "Lancamentos", "value": str(len(summary["entries"])), "tone": "warning"},
        {
            "label": "Pendencias",
            "value": str(len(summary["payables"]) + len(summary["receivables"])),
            "tone": "danger",
        },
    ]


def finance_status_bars(status_counts):
    total = max(sum(status_counts.values()), 1)
    colors = {
        "Pendentes": "warning",
        "Confirmadas": "primary",
        "Concluidas": "success",
        "Canceladas": "danger",
    }
    bars = []
    for label, value in status_counts.items():
        bars.append(
            {
                "label": label,
                "value": value,
                "width_pct": max(int((value / total) * 100), 4 if value else 0),
                "tone": colors.get(label, "primary"),
            }
        )
    return bars


FINANCE_CHECKLIST = [
    "Conferir reservas concluidas antes de marcar receita como recebida.",
    "Validar repasse do motorista antes de baixar contas a pagar.",
    "Comparar valor base, desconto e valor total de cada reserva.",
    "Exportar relatorio mensal apos conciliacao dos lancamentos.",
]

FINANCE_NAV = [
    {"key": "dashboard", "label": "Dashboard", "href": "/financeiro"},
    {"key": "lancamentos", "label": "Lancamentos", "href": "/financeiro/lancamentos"},
    {"key": "pagar", "label": "Contas a pagar", "href": "/financeiro/contas-a-pagar"},
    {"key": "receber", "label": "Contas a receber", "href": "/financeiro/contas-a-receber"},
    {"key": "relatorios", "label": "Relatorios", "href": "/financeiro/relatorios"},
]


def finance_context(reservations):
    summary = build_finance_summary(reservations)
    return {
        "summary": summary,
        "flow_bars": finance_flow_bars(summary),
        "health_items": finance_health_items(summary),
        "status_bars": finance_status_bars(summary["status_counts"]),
        "checklist": FINANCE_CHECKLIST,
        "finance_nav": FINANCE_NAV,
        "money_display": money_display,
    }
