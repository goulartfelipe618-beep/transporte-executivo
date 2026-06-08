"""Modulos HTML do painel web — leitura de dados reais do app (Supabase)."""
from __future__ import annotations

import re

from .company_model import is_corporate_client
from .data import PAGE_TITLES
from .portal_urls import company_portal_link
from .public_dtos import build_public_statistics_legacy
from .settings_store import load_settings
from .sistema_web_layout import esc


def _status_pill(status):
    raw = str(status or "—").strip()
    lower = raw.lower()
    css = "pill"
    if lower in {"ativa", "ativo", "concluida", "homologado", "publicado", "ok"}:
        css += " ok"
    elif lower in {"pendente", "em analise", "aguardando"}:
        css += " warn"
    elif lower in {"cancelada", "bloqueada", "inativo"}:
        css += " bad"
    return f'<span class="{css}">{esc(raw)}</span>'


def _cards(items):
    tiles = "".join(
        f'<div class="card"><div class="label">{esc(label)}</div><div class="value">{esc(value)}</div></div>'
        for label, value in items
    )
    return f'<div class="cards">{tiles}</div>'


def _panel(title, subtitle, table_html, *, note=""):
    note_html = f'<div class="note">{note}</div>' if note else ""
    return f"""{note_html}
<div class="panel"><div class="panel-head"><div><h2>{esc(title)}</h2><p>{esc(subtitle)}</p></div></div>
<div class="table-wrap">{table_html}</div></div>"""


def _table(columns, rows):
    if not rows:
        return '<div class="empty">Nenhum registro encontrado.</div>'
    head = "".join(f"<th>{esc(col)}</th>" for col in columns)
    body = []
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _money(value):
    try:
        amount = float(str(value or "0").replace(",", "."))
    except ValueError:
        amount = 0.0
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _finance_summary(reservations):
    active = [item for item in reservations if item.get("status") != "Cancelada"]
    revenue = 0.0
    repasse = 0.0
    receivable = 0.0
    payable = 0.0
    entries = []
    payables = []
    receivables = []
    for reservation in active:
        try:
            value = float(str(reservation.get("valor", "0")).replace(",", "."))
        except ValueError:
            value = 0.0
        try:
            rep = float(str(reservation.get("repasse", "0")).replace(",", "."))
        except ValueError:
            rep = 0.0
        revenue += value
        repasse += rep
        received = (reservation.get("status") or "") == "Concluida"
        number = reservation.get("numero", "")
        date_label = reservation.get("data") or "—"
        entries.append((date_label, "Entrada", f"Transfer {number}", _money(value), "Recebido" if received else "Previsto"))
        if not received:
            receivable += value
            receivables.append((date_label, reservation.get("cliente", ""), number, _money(value), reservation.get("status", "")))
        if rep > 0:
            entries.append((date_label, "Saida", f"Repasse {number}", _money(rep), "Pago" if received else "A pagar"))
            if not received:
                payable += rep
                payables.append((date_label, reservation.get("motorista", ""), number, _money(rep), "A pagar"))
    return {
        "revenue": revenue,
        "repasse": repasse,
        "receivable": receivable,
        "payable": payable,
        "entries": entries,
        "payables": payables,
        "receivables": receivables,
        "active_count": len(active),
    }


def _module_note(key):
    return (
        "Visualizacao web ativa com dados reais. "
        "Cadastro e edicao completa deste modulo serao liberados nas proximas versoes web; "
        "use o painel desktop para alteracoes avancadas ate la."
    )


def render_module(app, key):
    if key not in PAGE_TITLES:
        return _panel("Modulo", "Nao encontrado", '<div class="empty">Pagina invalida.</div>')
    note = _module_note(key)
    renderers = {
        "ABRANGENCIA": _render_abrangencia,
        "AGENDA": _render_agenda,
        "METRICAS": _render_metricas,
        "FIN_DASHBOARD": _render_fin_dashboard,
        "FIN_LANCAMENTOS": _render_fin_lancamentos,
        "FIN_CONTAS_PAGAR": _render_fin_pagar,
        "FIN_CONTAS_RECEBER": _render_fin_receber,
        "FIN_RELATORIOS": _render_fin_relatorios,
        "SOLICITACOES": _render_solicitacoes,
        "RESERVAS": _render_reservas,
        "MOTORISTAS": _render_motoristas,
        "CLIENTES": _render_clientes,
        "VEICULOS": _render_veiculos,
        "REDE": _render_rede,
        "REDE_SOLICITACOES": _render_rede_solicitacoes,
        "REDE_DASHBOARD": _render_rede_dashboard,
        "CONFIGURACOES": _render_configuracoes,
        "AUTOMACOES": _render_automacoes,
    }
    renderer = renderers.get(key)
    if not renderer:
        return _panel(PAGE_TITLES[key], "Em expansao", '<div class="empty">Modulo em implementacao.</div>', note=note)
    return renderer(app, note=note)


def _render_metricas(app, *, note=""):
    stats = build_public_statistics_legacy(app)
    cards = _cards(
        [
            ("Empresas ativas", stats.get("companies_active", 0)),
            ("Motoristas", stats.get("drivers_homologated", 0)),
            ("Cidades cobertas", stats.get("cities_covered", 0)),
            ("Pontos operacionais", stats.get("operational_points_total", 0)),
            ("Reservas", len(getattr(app, "reservations", []) or [])),
            ("Solicitacoes", len(getattr(app, "transport_requests", []) or [])),
        ]
    )
    rows = []
    for reservation in (getattr(app, "reservations", []) or [])[:12]:
        rows.append(
            (
                esc(reservation.get("numero", "")),
                esc(reservation.get("data", "")),
                esc(reservation.get("cliente", "")),
                esc(reservation.get("trajeto", "")),
                _status_pill(reservation.get("status")),
            )
        )
    table = _table(["Reserva", "Data", "Cliente", "Trajeto", "Status"], rows)
    return cards + _panel("Ultimas reservas", "Indicadores e movimentacao recente", table, note=note)


def _render_abrangencia(app, *, note=""):
    points = getattr(app, "operational_points", []) or []
    published = [p for p in points if p.get("portal_publicado", True)]
    by_type = {}
    by_uf = {}
    for point in published:
        tipo = str(point.get("tipo", "Outro"))
        by_type[tipo] = by_type.get(tipo, 0) + 1
        uf = str(point.get("estado_uf", "") or "—")
        by_uf[uf] = by_uf.get(uf, 0) + 1
    cards = _cards(
        [
            ("Pontos publicados", len(published)),
            ("Tipos", len(by_type)),
            ("UFs", len(by_uf)),
            ("Total cadastrado", len(points)),
        ]
    )
    type_rows = [(esc(k), esc(v)) for k, v in sorted(by_type.items(), key=lambda x: (-x[1], x[0]))]
    uf_rows = [(esc(k), esc(v)) for k, v in sorted(by_uf.items(), key=lambda x: (-x[1], x[0]))[:15]]
    return (
        cards
        + _panel("Pontos por tipo", "Distribuicao da rede operacional", _table(["Tipo", "Qtd"], type_rows), note=note)
        + _panel("Cobertura por UF", "Estados com pontos publicados", _table(["UF", "Pontos"], uf_rows))
    )


def _render_agenda(app, *, note=""):
    reservations = sorted(getattr(app, "reservations", []) or [], key=lambda r: str(r.get("data", "")))
    rows = []
    for item in reservations[:40]:
        rows.append(
            (
                esc(item.get("data", "")),
                esc(item.get("hora", item.get("horario", ""))),
                esc(item.get("cliente", "")),
                esc(item.get("origem", "")),
                esc(item.get("destino", "")),
                esc(item.get("motorista", "")),
                _status_pill(item.get("status")),
            )
        )
    return _panel("Agenda de servicos", "Programacao e reservas por data", _table(
        ["Data", "Hora", "Cliente", "Origem", "Destino", "Motorista", "Status"], rows
    ), note=note)


def _render_clientes(app, *, note=""):
    clients = [c for c in (getattr(app, "clients", []) or []) if is_corporate_client(c)]
    cards = _cards([("Empresas", len(clients)), ("Ativas", sum(1 for c in clients if c.get("status_empresa") == "Ativa"))])
    rows = []
    for client in clients:
        name = client.get("nome_fantasia") or client.get("razao_social") or client.get("nome", "")
        link = company_portal_link(client)
        link_html = f'<a href="{esc(link)}" target="_blank" rel="noopener">{esc(link)}</a>' if link else "—"
        rows.append(
            (
                esc(name),
                esc(client.get("cnpj", "")),
                esc(client.get("id", "")),
                _status_pill(client.get("status_empresa", "Ativa")),
                link_html,
            )
        )
    return cards + _panel("Empresas corporativas", "Carteira de clientes PJ", _table(
        ["Empresa", "CNPJ", "ID", "Status", "Portal"], rows
    ), note=note)


def _render_motoristas(app, *, note=""):
    drivers = getattr(app, "drivers", []) or []
    cards = _cards([("Motoristas", len(drivers)), ("Ativos", sum(1 for d in drivers if str(d.get("status", "")).lower() == "ativo"))])
    rows = []
    for driver in drivers:
        rows.append(
            (
                esc(driver.get("nome", "")),
                esc(driver.get("telefone", "")),
                esc(driver.get("cidade", driver.get("regiao", ""))),
                esc(driver.get("categoria", "")),
                _status_pill(driver.get("status")),
            )
        )
    return cards + _panel("Cadastro de motoristas", "Equipe homologada e parceiros", _table(
        ["Nome", "Telefone", "Regiao", "Categoria", "Status"], rows
    ), note=note)


def _render_veiculos(app, *, note=""):
    vehicles = getattr(app, "vehicles", []) or []
    cards = _cards([("Veiculos", len(vehicles)), ("Publicados", sum(1 for v in vehicles if v.get("portal_publicado")))])
    rows = []
    for vehicle in vehicles:
        rows.append(
            (
                esc(vehicle.get("placa", "")),
                esc(vehicle.get("modelo", "")),
                esc(vehicle.get("categoria", "")),
                esc(vehicle.get("capacidade", "")),
                _status_pill(vehicle.get("status", "Ativo")),
            )
        )
    return cards + _panel("Frota de veiculos", "Catalogo operacional", _table(
        ["Placa", "Modelo", "Categoria", "Capacidade", "Status"], rows
    ), note=note)


def _render_reservas(app, *, note=""):
    reservations = list(getattr(app, "reservations", []) or [])
    cards = _cards([
        ("Total", len(reservations)),
        ("Ativas", sum(1 for r in reservations if r.get("status") != "Cancelada")),
        ("Concluidas", sum(1 for r in reservations if r.get("status") == "Concluida")),
    ])
    rows = []
    for item in reservations[:50]:
        rows.append(
            (
                esc(item.get("numero", "")),
                esc(item.get("data", "")),
                esc(item.get("cliente", "")),
                esc(item.get("trajeto", "")),
                esc(item.get("motorista", "")),
                esc(_money(item.get("valor", 0))),
                _status_pill(item.get("status")),
            )
        )
    return cards + _panel("Reservas confirmadas", "Operacao e alocacao", _table(
        ["Codigo", "Data", "Cliente", "Trajeto", "Motorista", "Valor", "Status"], rows
    ), note=note)


def _render_solicitacoes(app, *, note=""):
    requests = getattr(app, "transport_requests", []) or []
    rows = []
    for item in requests[:50]:
        rows.append(
            (
                esc(item.get("id", "")),
                esc(item.get("cliente", item.get("empresa", ""))),
                esc(item.get("data", item.get("criado_em", ""))),
                esc(item.get("origem", "")),
                esc(item.get("destino", "")),
                _status_pill(item.get("status")),
            )
        )
    return _panel("Solicitacoes de transfer", "Fila de pedidos recebidos", _table(
        ["ID", "Cliente", "Data", "Origem", "Destino", "Status"], rows
    ), note=note)


def _render_fin_dashboard(app, *, note=""):
    summary = _finance_summary(getattr(app, "reservations", []) or [])
    cards = _cards([
        ("Receita prevista", _money(summary["revenue"])),
        ("Repasse motoristas", _money(summary["repasse"])),
        ("A receber", _money(summary["receivable"])),
        ("A pagar", _money(summary["payable"])),
        ("Reservas ativas", summary["active_count"]),
    ])
    return cards + _panel("Financeiro", "Resumo consolidado das reservas", '<div class="empty">Use Lancamentos, Contas a pagar/receber e Relatorios no menu.</div>', note=note)


def _render_fin_lancamentos(app, *, note=""):
    summary = _finance_summary(getattr(app, "reservations", []) or [])
    rows = [(
        esc(d), esc(t), esc(desc), esc(val), _status_pill(st),
    ) for d, t, desc, val, st in summary["entries"][:60]]
    return _panel("Lancamentos", "Entradas e saidas derivadas das reservas", _table(
        ["Data", "Tipo", "Descricao", "Valor", "Status"], rows
    ), note=note)


def _render_fin_pagar(app, *, note=""):
    summary = _finance_summary(getattr(app, "reservations", []) or [])
    rows = [(esc(d), esc(m), esc(n), esc(v), _status_pill(s)) for d, m, n, v, s in summary["payables"][:50]]
    return _panel("Contas a pagar", "Repasses e obrigacoes pendentes", _table(
        ["Data", "Motorista", "Reserva", "Valor", "Status"], rows
    ), note=note)


def _render_fin_receber(app, *, note=""):
    summary = _finance_summary(getattr(app, "reservations", []) or [])
    rows = [(esc(d), esc(c), esc(n), esc(v), _status_pill(s)) for d, c, n, v, s in summary["receivables"][:50]]
    return _panel("Contas a receber", "Receitas pendentes de recebimento", _table(
        ["Data", "Cliente", "Reserva", "Valor", "Status"], rows
    ), note=note)


def _render_fin_relatorios(app, *, note=""):
    summary = _finance_summary(getattr(app, "reservations", []) or [])
    margin = summary["revenue"] - summary["repasse"]
    cards = _cards([
        ("Receita", _money(summary["revenue"])),
        ("Custos repasse", _money(summary["repasse"])),
        ("Margem estimada", _money(margin)),
    ])
    return cards + _panel("Relatorios", "Leitura executiva do periodo", '<div class="empty">Exportacao PDF/CSV permanece no painel desktop.</div>', note=note)


def _render_rede(app, *, note=""):
    networks = getattr(app, "partner_networks", []) or []
    rows = []
    for net in networks:
        rows.append(
            (
                esc(net.get("nome", "")),
                esc(net.get("slug", "")),
                esc(net.get("codigo", net.get("codigo_acesso", ""))),
                esc(net.get("empresa_vinculada", "")),
                _status_pill(net.get("status", "Ativa")),
            )
        )
    return _panel("Rede de empresas parceiras", "Cadastro de redes e QR", _table(
        ["Rede", "Slug", "Codigo", "Empresa", "Status"], rows
    ), note=note)


def _render_rede_solicitacoes(app, *, note=""):
    logs = getattr(app, "network_access_logs", []) or []
    rows = []
    for item in logs[:50]:
        rows.append(
            (
                esc(item.get("criado_em", item.get("data", ""))),
                esc(item.get("rede", item.get("network_id", ""))),
                esc(item.get("motorista", item.get("driver_id", ""))),
                esc(item.get("acao", item.get("evento", ""))),
                esc(item.get("detalhe", item.get("resumo", ""))),
            )
        )
    return _panel("Solicitacoes da rede", "Acessos e eventos do motor", _table(
        ["Data", "Rede", "Motorista", "Acao", "Detalhe"], rows
    ), note=note)


def _render_rede_dashboard(app, *, note=""):
    networks = getattr(app, "partner_networks", []) or []
    contributors = getattr(app, "network_contributors", []) or []
    commissions = getattr(app, "network_commissions", []) or []
    cards = _cards([
        ("Redes", len(networks)),
        ("Colaboradores", len(contributors)),
        ("Comissoes", len(commissions)),
    ])
    return cards + _panel("Dashboard comercial", "Visao da operacao em rede", '<div class="empty">Graficos detalhados no painel desktop.</div>', note=note)


def _render_configuracoes(app, *, note=""):
    settings = load_settings()
    rows = []
    for key, value in sorted(settings.items()):
        if not str(value or "").strip():
            continue
        if key in {"assinatura", "logo_global", "logo_contratual"} and len(str(value)) > 80:
            value = "(arquivo configurado)"
        rows.append((esc(key.replace("_", " ").title()), esc(value)))
    return _panel("Configuracoes do sistema", "Parametros gerais (somente leitura na web)", _table(
        ["Campo", "Valor"], rows
    ), note=note + " Edicao de configuracoes: painel desktop.")


def _render_automacoes(app, *, note=""):
    try:
        from .automations import ensure_automations_loaded

        ensure_automations_loaded(app)
    except Exception:
        pass
    items = getattr(app, "automations", []) or []
    rows = []
    for item in items:
        rows.append(
            (
                esc(item.get("nome", item.get("tipo", ""))),
                esc(item.get("dominio", item.get("domain", ""))),
                esc(item.get("token", "")),
                _status_pill("Ativo" if item.get("ativo", True) else "Inativo"),
            )
        )
    return _panel("Automacoes operacionais", "Webhooks e rotinas configuradas", _table(
        ["Automacao", "Dominio", "Token", "Status"], rows
    ), note=note)


def normalize_module_key(slug):
    if not slug:
        return "ABRANGENCIA"
    key = re.sub(r"[^a-z0-9_]", "", str(slug).strip().lower())
    for valid in PAGE_TITLES:
        if valid.lower() == key:
            return valid
    aliases = {
        "empresas": "CLIENTES",
        "financeiro": "FIN_DASHBOARD",
        "transfer": "RESERVAS",
    }
    return aliases.get(key)
