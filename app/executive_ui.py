"""Painel executivo estrategico do backoffice master."""
import tkinter as tk

from .platform import build_executive_stats, ensure_platform_collections
from .theme import COLORS, FONTS, panel_frame, styled_button


def render_executive_dashboard(parent, app):
    ensure_platform_collections(app)
    stats = build_executive_stats(app)

    parent.configure(bg=COLORS["bg"])
    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 12))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Painel Executivo", bg=COLORS["bg"], fg=COLORS["text"], font=FONTS["title"]).pack(anchor="w")
    tk.Label(
        title_box,
        text="Visao estrategica da plataforma nacional. Consolida empresas, motoristas, cobertura, leads e solicitacoes recebidas.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=FONTS["small"],
        wraplength=760,
        justify="left",
    ).pack(anchor="w", pady=(2, 0))
    styled_button(header, "Atualizar", style="secondary", command=lambda: render_executive_dashboard(parent, app)).pack(side="right", anchor="n")

    row1 = tk.Frame(parent, bg=COLORS["bg"])
    row1.pack(fill="x", pady=(0, 10))
    cards_row1 = [
        ("Empresas cadastradas", stats["empresas_cadastradas"], "base corporativa"),
        ("Empresas ativas", stats["empresas_ativas"], "operacao comercial"),
        ("Motoristas homologados", stats["motoristas_homologados"], "base operacional"),
        ("Reservas", stats["reservas_total"], "confirmadas na plataforma"),
    ]
    for index, (title, value, hint) in enumerate(cards_row1):
        _metric_card(row1, title, str(value), hint).pack(side="left", fill="x", expand=True, padx=(0 if index == 0 else 8, 0))

    row2 = tk.Frame(parent, bg=COLORS["bg"])
    row2.pack(fill="x", pady=(0, 10))
    cards_row2 = [
        ("Estados cobertos", stats["estados_cobertos"], "pontos operacionais"),
        ("Cidades cobertas", stats["cidades_cobertas"], "distribuicao geografica"),
        ("Leads recebidos", stats["leads_empresas"] + stats["leads_motoristas"], f'{stats["leads_novos"]} novos'),
        ("Solicitacoes recebidas", stats["solicitacoes_recebidas"], f'{stats["solicitacoes_pendentes"]} pendentes'),
    ]
    for index, (title, value, hint) in enumerate(cards_row2):
        _metric_card(row2, title, str(value), hint).pack(side="left", fill="x", expand=True, padx=(0 if index == 0 else 8, 0))

    body = tk.Frame(parent, bg=COLORS["bg"])
    body.pack(fill="both", expand=True)
    body.grid_columnconfigure(0, weight=1, uniform="exec")
    body.grid_columnconfigure(1, weight=1, uniform="exec")
    body.grid_rowconfigure(0, weight=1)

    left = panel_frame(body)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    tk.Label(left, text="Fluxo futuro Site -> Painel", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["subtitle"]).pack(anchor="w", padx=12, pady=(12, 8))
    flow = tk.Frame(left, bg=COLORS["panel"])
    flow.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    steps = [
        "Site publico envia formularios",
        "Webhooks / APIs recebem no painel master",
        "Leads e solicitacoes entram em triagem",
        "Empresas e motoristas sao homologados",
        "Reservas alimentam operacao e financeiro",
    ]
    for step in steps:
        tk.Label(flow, text=f"  >  {step}", bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["body"], anchor="w", justify="left").pack(anchor="w", pady=3)

    right = panel_frame(body)
    right.grid(row=0, column=1, sticky="nsew")
    tk.Label(right, text="Atalhos operacionais", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["subtitle"]).pack(anchor="w", padx=12, pady=(12, 8))
    shortcuts = tk.Frame(right, bg=COLORS["panel"])
    shortcuts.pack(fill="x", padx=12, pady=(0, 12))
    for label, key in [
        ("Leads de empresas", "LEADS_EMPRESAS"),
        ("Leads de motoristas", "LEADS_MOTORISTAS"),
        ("Solicitacoes de transporte", "SOLICITACOES"),
        ("Integracoes", "INTEGRACOES"),
        ("Log de eventos", "LOG_EVENTOS"),
        ("Abrangencia nacional", "ABRANGENCIA"),
    ]:
        styled_button(shortcuts, label, style="outline_primary", command=lambda page=key: app.show_page(page)).pack(fill="x", pady=4)


def _metric_card(parent, title, value, hint):
    card = panel_frame(parent)
    tk.Label(card, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(10, 0))
    tk.Label(card, text=value, bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 22)).pack(anchor="w", padx=12)
    tk.Label(card, text=hint, bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=12, pady=(0, 10))
    return card
