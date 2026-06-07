import tkinter as tk
from datetime import datetime

from .api_gateway import start_api_gateway_server
from .automations import ensure_automations_loaded, render_automations, start_automation_webhook_server
from .partner_network import ensure_partner_networks
from .partner_network_dashboard import render_rede_dashboard
from .partner_network_portal import start_partner_portal_server
from .rede_solicitacoes_ui import render_rede_solicitacoes
from .rede_ui import render_rede
from .company_model import ensure_company_portal_structure, is_corporate_client
from .company_portal import company_portal_url, start_company_portal_server
from .data import PAGE_MENU_GROUP, PAGE_TITLES, REGISTRY_PAGES, TRANSFER_PAGES
from .full_features import render_clients, render_settings
from .coverage_ui import render_abrangencia
from .operational_network import ensure_operational_network
from .pages import (
    render_agenda,
    render_finance,
    render_metricas,
    render_registry,
    render_transfer,
)
from .portal_auth import ensure_portal_security
from .portal_server import start_driver_portal_server
from .repository import AppRepository
from .reservations import render_reservations_page
from .sidebar import SIDEBAR_MINI_WIDTH, SIDEBAR_WIDTH, build_sidebar, build_sidebar_mini, group_text
from .branding import apply_branding
from .components import install_global_input_rules
from .theme import COLORS, FONTS, badge_label, configure_styles, styled_button
from .version import APP_BUILD


class TransferSystemApp(tk.Tk):
    def __init__(self):
        super().__init__()
        branding = apply_branding()
        self.brand_name = branding["nome_projeto"]
        self.title(f"{self.brand_name} - Build {APP_BUILD}")
        self.geometry("1380x800")
        self.minsize(1100, 700)
        self.configure(bg=COLORS["bg"])

        self.repo = AppRepository.bootstrap(self)

        self.active_menu = None
        self.submenu_open = {"FINANCEIRO": False, "TRANSFER": False, "REDE": False, "SISTEMA": False}
        self.menu_buttons = {}
        self.submenu_frames = {}
        self.sidebar_collapsed = False

        ensure_automations_loaded(self)
        _, network_changed = ensure_operational_network(self)
        portal_changed = ensure_portal_security(self)
        rede_changed = ensure_partner_networks(self)
        if network_changed or portal_changed or rede_changed:
            self.save_state()
        start_automation_webhook_server(self)
        start_api_gateway_server(self)
        start_driver_portal_server(self)
        start_company_portal_server(self)
        start_partner_portal_server(self)
        self._ensure_company_portals()

        configure_styles(self)
        install_global_input_rules(self)
        self.build_layout()
        self.show_page("ABRANGENCIA")

    def save_state(self):
        self.repo.persist()

    def _ensure_company_portals(self):
        base = company_portal_url(self)
        changed = False
        for index, client in enumerate(self.clients):
            if not is_corporate_client(client):
                continue
            if client.get("portal_key") and client.get("portal_link"):
                continue
            self.clients[index] = ensure_company_portal_structure(client, base, self.clients)
            changed = True
        if changed:
            self.save_state()

    def refresh_reservations(self):
        if self.active_menu == "RESERVAS":
            self.show_page("RESERVAS")

    def refresh_branding(self):
        branding = apply_branding()
        self.brand_name = branding["nome_projeto"]
        self.title(f"{self.brand_name} - Build {APP_BUILD}")
        configure_styles(self)
        collapsed = self.sidebar_collapsed
        for widget in self.sidebar.winfo_children():
            widget.destroy()
        for widget in self.sidebar_mini.winfo_children():
            widget.destroy()
        build_sidebar(self)
        build_sidebar_mini(self)
        if collapsed:
            self.sidebar.pack_forget()
            self.sidebar_mini.pack(fill="both", expand=True)
            self.sidebar_shell.configure(width=SIDEBAR_MINI_WIDTH)
        else:
            self.sidebar_mini.pack_forget()
            self.sidebar.pack(fill="both", expand=True)
            self.sidebar_shell.configure(width=SIDEBAR_WIDTH)
        self.refresh_menu_state()
        if self.active_menu:
            self.show_page(self.active_menu)

    def build_layout(self):
        self.sidebar_shell = tk.Frame(self, bg=COLORS["sidebar"], width=SIDEBAR_WIDTH)
        self.sidebar_shell.pack(side="left", fill="y")
        self.sidebar_shell.pack_propagate(False)

        self.sidebar = tk.Frame(self.sidebar_shell, bg=COLORS["sidebar"])
        self.sidebar.pack(fill="both", expand=True)

        self.sidebar_mini = tk.Frame(self.sidebar_shell, bg=COLORS["sidebar"])

        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.pack(side="right", fill="both", expand=True)

        build_sidebar(self)
        build_sidebar_mini(self)
        self.build_topbar()

        self.content = tk.Frame(self.main, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True, padx=16, pady=(10, 14))

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        if self.sidebar_collapsed:
            self.sidebar.pack_forget()
            self.sidebar_mini.pack(fill="both", expand=True)
            self.sidebar_shell.configure(width=SIDEBAR_MINI_WIDTH)
        else:
            self.sidebar_mini.pack_forget()
            self.sidebar.pack(fill="both", expand=True)
            self.sidebar_shell.configure(width=SIDEBAR_WIDTH)
            if hasattr(self, "sidebar_canvas"):
                self.after(50, lambda: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))

    def build_topbar(self):
        self.topbar = tk.Frame(
            self.main,
            bg=COLORS["panel"],
            height=62,
            highlightthickness=0,
        )
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        accent = tk.Frame(self.topbar, bg=COLORS["primary"], width=4)
        accent.pack(side="left", fill="y")

        self.page_title = tk.Label(
            self.topbar,
            text="Dashboard",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        )
        self.page_title.pack(side="left", padx=(16, 14), pady=14)

        right = tk.Frame(self.topbar, bg=COLORS["panel"])
        right.pack(side="right", padx=16, pady=12)

        badge_label(right, f"Build {APP_BUILD}", tone="neutral").pack(side="left", padx=(0, 8))
        badge_label(right, datetime.now().strftime("%d/%m/%Y"), tone="primary").pack(side="left", padx=(0, 12))

        user = tk.Frame(right, bg=COLORS["panel"])
        user.pack(side="left")
        tk.Label(user, text="Administrador", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 9)).pack(anchor="e")
        tk.Label(user, text="Central Operacional", bg=COLORS["panel"], fg=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="e")

        tk.Frame(self.main, bg=COLORS["line"], height=1).pack(fill="x")

    def add_menu_button(self, parent, key, label, icon):
        btn = tk.Button(
            parent,
            text=f"  {icon}   {label.upper()}",
            anchor="w",
            bd=0,
            relief="flat",
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_text"],
            activebackground=COLORS["sidebar_hover"],
            activeforeground=COLORS["white"],
            font=FONTS["small"],
            padx=12,
            pady=8,
            cursor="hand2",
            highlightthickness=0,
            command=lambda: self.show_page(key),
        )
        btn.pack(fill="x", pady=2)
        btn.bind("<Enter>", lambda _event, button=btn: self.hover_menu_button(button))
        btn.bind("<Leave>", lambda _event, button=btn, item_key=key: self.leave_menu_button(button, item_key))
        self.menu_buttons[key] = btn

    def add_group_button(self, parent, key):
        container = tk.Frame(parent, bg=COLORS["sidebar"])
        container.pack(fill="x", pady=(10 if key == "FINANCEIRO" else 4, 2))

        btn = tk.Button(
            container,
            text=group_text(key, self.submenu_open[key]),
            anchor="w",
            bd=0,
            relief="flat",
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_text"],
            activebackground=COLORS["sidebar_hover"],
            activeforeground=COLORS["white"],
            font=("Segoe UI Semibold", 9),
            padx=12,
            pady=8,
            cursor="hand2",
            highlightthickness=0,
            command=lambda: self.toggle_group(key),
        )
        btn.pack(fill="x")
        self.menu_buttons[key] = btn

        frame = tk.Frame(container, bg=COLORS["sidebar"])
        self.submenu_frames[key] = frame
        if self.submenu_open[key]:
            frame.pack(fill="x", padx=(8, 0))

    def add_submenu_button(self, group, key, label):
        frame = self.submenu_frames[group]
        btn = tk.Button(
            frame,
            text=f"      {label.upper()}",
            anchor="w",
            bd=0,
            relief="flat",
            bg=COLORS["sidebar"],
            fg=COLORS["sidebar_text"],
            activebackground=COLORS["sidebar_hover"],
            activeforeground=COLORS["white"],
            font=FONTS["small"],
            padx=14,
            pady=6,
            cursor="hand2",
            highlightthickness=0,
            command=lambda: self.show_page(key),
        )
        btn.pack(fill="x", pady=1)
        self.menu_buttons[key] = btn

    def hover_menu_button(self, button):
        if button.cget("bg") != COLORS["sidebar_active"]:
            button.configure(bg=COLORS["sidebar_hover"], fg=COLORS["white"])

    def leave_menu_button(self, button, key):
        if self.active_menu != key:
            button.configure(bg=self.inactive_menu_bg(key), fg=self.inactive_menu_color(key))

    def toggle_group(self, key):
        self.submenu_open[key] = not self.submenu_open[key]
        frame = self.submenu_frames[key]
        if self.submenu_open[key]:
            frame.pack(fill="x", padx=(8, 0))
        else:
            frame.pack_forget()
        self.menu_buttons[key].configure(text=group_text(key, self.submenu_open[key]))
        if hasattr(self, "sidebar_canvas"):
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

    def _ensure_group_visible(self, key):
        group = PAGE_MENU_GROUP.get(key)
        if not group or self.submenu_open.get(group):
            return
        self.submenu_open[group] = True
        frame = self.submenu_frames[group]
        frame.pack(fill="x", padx=(8, 0))
        self.menu_buttons[group].configure(text=group_text(group, True))
        if hasattr(self, "sidebar_canvas"):
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))

    def show_page(self, key):
        self._ensure_group_visible(key)
        self.active_menu = key
        self.refresh_menu_state()
        self.clear_content()
        self.page_title.configure(text=PAGE_TITLES.get(key, key.title()))

        if key == "ABRANGENCIA":
            render_abrangencia(self.content, self)
        elif key == "AGENDA":
            render_agenda(self.content, self)
        elif key == "METRICAS":
            render_metricas(self.content, self)
        elif key.startswith("FIN_"):
            render_finance(self.content, self, key)
        elif key == "RESERVAS":
            render_reservations_page(self.content, self)
        elif key in TRANSFER_PAGES:
            render_transfer(self.content, key)
        elif key == "CLIENTES":
            render_clients(self.content, self)
        elif key == "REDE":
            render_rede(self.content, self)
        elif key == "REDE_SOLICITACOES":
            render_rede_solicitacoes(self.content, self)
        elif key == "REDE_DASHBOARD":
            render_rede_dashboard(self.content, self)
        elif key in REGISTRY_PAGES:
            render_registry(self.content, key)
        elif key == "CONFIGURACOES":
            render_settings(self.content, self)
        elif key == "AUTOMACOES":
            render_automations(self.content, self)

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def refresh_menu_state(self):
        for key, btn in self.menu_buttons.items():
            is_active = key == self.active_menu
            if is_active:
                btn.configure(bg=COLORS["sidebar_active"], fg=COLORS["white"])
            else:
                btn.configure(bg=self.inactive_menu_bg(key), fg=self.inactive_menu_color(key))

    def inactive_menu_color(self, key):
        return COLORS["sidebar_text"]

    def inactive_menu_bg(self, key):
        return COLORS["sidebar"]
