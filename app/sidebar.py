import tkinter as tk

from .branding import brand_display_name, brand_initials
from .data import MENU_GROUPS
from .theme import COLORS, FONTS, styled_button
from .version import APP_BUILD

SIDEBAR_WIDTH = 260
SIDEBAR_MINI_WIDTH = 52


def build_sidebar(app):
    toolbar = tk.Frame(app.sidebar, bg=COLORS["sidebar"])
    toolbar.pack(fill="x", padx=10, pady=(10, 0))
    tk.Button(
        toolbar,
        text="◀",
        bg=COLORS["sidebar_soft"],
        fg=COLORS["sidebar_text"],
        activebackground=COLORS["sidebar_hover"],
        activeforeground=COLORS["white"],
        bd=0,
        relief="flat",
        font=FONTS.get("semibold_sm", ("Segoe UI Semibold", 9)),
        padx=8,
        pady=4,
        cursor="hand2",
        command=app.toggle_sidebar,
    ).pack(side="right")

    brand = tk.Frame(app.sidebar, bg=COLORS["sidebar"])
    brand.pack(fill="x", padx=16, pady=(10, 10))

    logo_row = tk.Frame(brand, bg=COLORS["sidebar"])
    logo_row.pack(fill="x")
    initials = brand_initials(getattr(app, "brand_name", None))
    app._brand_initials_label = tk.Label(
        logo_row,
        text=initials,
        bg=COLORS["sidebar_active"],
        fg=COLORS["white"],
        font=FONTS.get("semibold_sm", ("Segoe UI Semibold", 11)),
        width=3,
        pady=4,
    )
    app._brand_initials_label.pack(side="left")
    title_box = tk.Frame(logo_row, bg=COLORS["sidebar"])
    title_box.pack(side="left", padx=(10, 0))
    brand_title = getattr(app, "brand_name", None) or brand_display_name()
    app._brand_title_label = tk.Label(
        title_box,
        text=str(brand_title).upper(),
        bg=COLORS["sidebar"],
        fg=COLORS["white"],
        font=FONTS["brand"],
    )
    app._brand_title_label.pack(anchor="w")
    tk.Label(
        title_box,
        text="PAINEL OPERACIONAL",
        bg=COLORS["sidebar"],
        fg=COLORS["sidebar_text"],
        font=FONTS["tiny"],
    ).pack(anchor="w")

    tk.Frame(app.sidebar, bg=COLORS["sidebar_soft"], height=1).pack(fill="x", padx=16, pady=(8, 10))

    scroll_host = tk.Frame(app.sidebar, bg=COLORS["sidebar"])
    scroll_host.pack(fill="both", expand=True)

    canvas = tk.Canvas(scroll_host, bg=COLORS["sidebar"], highlightthickness=0, width=240)
    scrollbar = tk.Scrollbar(scroll_host, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    menu_area = tk.Frame(canvas, bg=COLORS["sidebar"])
    menu_window = canvas.create_window((0, 0), window=menu_area, anchor="nw", width=236)

    def _sync_scroll_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _sync_menu_width(event):
        canvas.itemconfigure(menu_window, width=max(event.width, 200))

    def _on_mousewheel(event):
        bbox = canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= canvas.winfo_height():
            return "break"
        top, bottom = canvas.yview()
        delta = int(-1 * (event.delta / 120))
        if delta < 0 and top <= 0.001:
            canvas.yview_moveto(0)
            return "break"
        if delta > 0 and bottom >= 0.999:
            return "break"
        canvas.yview_scroll(delta, "units")
        return "break"

    menu_area.bind("<Configure>", _sync_scroll_region)
    canvas.bind("<Configure>", _sync_menu_width)
    canvas.bind("<MouseWheel>", _on_mousewheel)
    menu_area.bind("<MouseWheel>", _on_mousewheel)
    scroll_host.bind("<MouseWheel>", _on_mousewheel)
    app.sidebar_canvas = canvas

    app.add_menu_button(menu_area, "ABRANGENCIA", "ABRANGENCIA", "🗺️")
    app.add_menu_button(menu_area, "AGENDA", "AGENDA", "📅")
    app.add_menu_button(menu_area, "METRICAS", "METRICAS", "📊")
    app.add_group_button(menu_area, "FINANCEIRO")
    app.add_submenu_button("FINANCEIRO", "FIN_DASHBOARD", "DASHBOARD")
    app.add_submenu_button("FINANCEIRO", "FIN_LANCAMENTOS", "LANCAMENTOS")
    app.add_submenu_button("FINANCEIRO", "FIN_CONTAS_PAGAR", "CONTAS A PAGAR")
    app.add_submenu_button("FINANCEIRO", "FIN_CONTAS_RECEBER", "CONTAS A RECEBER")
    app.add_submenu_button("FINANCEIRO", "FIN_RELATORIOS", "RELATORIOS")
    app.add_group_button(menu_area, "TRANSFER")
    app.add_submenu_button("TRANSFER", "SOLICITACOES", "SOLICITACOES")
    app.add_submenu_button("TRANSFER", "RESERVAS", "RESERVAS")
    app.add_menu_button(menu_area, "MOTORISTAS", "MOTORISTAS", "👤")
    app.add_menu_button(menu_area, "CLIENTES", "EMPRESAS", "🏢")
    app.add_menu_button(menu_area, "VEICULOS", "VEICULOS", "🚗")
    app.add_group_button(menu_area, "REDE")
    app.add_submenu_button("REDE", "REDE", "CADASTRO")
    app.add_submenu_button("REDE", "REDE_SOLICITACOES", "SOLICITACOES")
    app.add_submenu_button("REDE", "REDE_DASHBOARD", "DASHBOARD")
    app.add_group_button(menu_area, "SISTEMA")
    app.add_submenu_button("SISTEMA", "CONFIGURACOES", "CONFIGURACOES")
    app.add_submenu_button("SISTEMA", "AUTOMACOES", "AUTOMACOES")

    build_status_footer(app.sidebar)


def build_sidebar_mini(app):
    initials = brand_initials(getattr(app, "brand_name", None))
    tk.Label(
        app.sidebar_mini,
        text=initials,
        bg=COLORS["sidebar_active"],
        fg=COLORS["white"],
        font=FONTS.get("semibold_sm", ("Segoe UI Semibold", 10)),
        width=3,
        pady=6,
    ).pack(pady=(16, 12))
    tk.Button(
        app.sidebar_mini,
        text="▶",
        bg=COLORS["sidebar_soft"],
        fg=COLORS["sidebar_text"],
        activebackground=COLORS["sidebar_hover"],
        activeforeground=COLORS["white"],
        bd=0,
        relief="flat",
        font=FONTS.get("semibold_sm", ("Segoe UI Semibold", 9)),
        padx=8,
        pady=4,
        cursor="hand2",
        command=app.toggle_sidebar,
    ).pack(pady=4)


def build_status_footer(parent):
    footer = tk.Frame(parent, bg=COLORS["sidebar_soft"], highlightthickness=0)
    footer.pack(side="bottom", fill="x", padx=10, pady=(8, 14))
    tk.Label(
        footer,
        text="STATUS DO SISTEMA",
        bg=COLORS["sidebar_soft"],
        fg=COLORS["sidebar_text"],
        font=("Segoe UI Semibold", 8),
    ).pack(anchor="w", padx=12, pady=(10, 2))
    status_row = tk.Frame(footer, bg=COLORS["sidebar_soft"])
    status_row.pack(anchor="w", padx=12, pady=(0, 10))
    tk.Label(status_row, text="●", bg=COLORS["sidebar_soft"], fg=COLORS["success"], font=FONTS["small"]).pack(side="left")
    tk.Label(
        status_row,
        text=f" ONLINE  ·  BUILD {APP_BUILD}",
        bg=COLORS["sidebar_soft"],
        fg=COLORS["sidebar_text"],
        font=FONTS["tiny"],
    ).pack(side="left")


def group_text(key, submenu_open):
    label, icon = MENU_GROUPS[key]
    marker = "▾" if submenu_open else "▸"
    return f" {marker}  {icon}  {label.upper()}"
