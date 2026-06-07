import json
import os
import secrets
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .platform_contract import AUTOMATION_WEBHOOK_PORT

AUTOMATION_TYPES = {
    "transfer_request": "AUTOMACAO SOLICITACAO DE TRANSFER",
    "driver_request": "AUTOMACAO SOLICITACAO PARA SER MOTORISTA",
}

AUTOMATION_PORT = AUTOMATION_WEBHOOK_PORT
AUTOMATIONS_FILE = os.path.join("data", "automations.json")
TOKEN_BYTES = 24


def _lazy_ui():
    """Imports Tkinter apenas para a UI desktop (nao usado no runtime headless)."""
    import tkinter as tk
    from tkinter import messagebox, ttk

    from .components import resolve_widget_value, setup_placeholder
    from .table_ui import render_action_buttons
    from .theme import COLORS, FONTS, styled_button

    return tk, messagebox, ttk, resolve_widget_value, setup_placeholder, render_action_buttons, COLORS, FONTS, styled_button


def automation_url(token):
    return f"http://127.0.0.1:{AUTOMATION_PORT}/webhook/{token}"


def normalize_domain(domain):
    raw = (domain or "").strip().rstrip("/")
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.netloc or parsed.path).split("/")[0].lower()
    scheme = parsed.scheme if parsed.netloc else "https"
    if not host or "." not in host:
        return ""
    return f"{scheme}://{host}"


def _request_origin(headers):
    origin = normalize_domain(headers.get("Origin", ""))
    if origin:
        return origin
    referer = headers.get("Referer", "")
    if referer:
        parsed = urlparse(referer)
        return normalize_domain(f"{parsed.scheme}://{parsed.netloc}")
    return ""


def _type_from_legacy(item):
    raw = (item.get("tipo") or item.get("type") or "").lower()
    label = (item.get("type_label") or item.get("tipo_label") or "").lower()
    if "motorista" in raw or "motorista" in label or raw == "driver_request":
        return "driver_request"
    if "transfer" in raw or "transfer" in label or raw == "transfer_request":
        return "transfer_request"
    return ""


def _normalize_automation(item):
    type_key = _type_from_legacy(item)
    if type_key not in AUTOMATION_TYPES:
        return None
    token = item.get("token") or secrets.token_urlsafe(TOKEN_BYTES)
    name = item.get("nome") or item.get("name") or AUTOMATION_TYPES[type_key].title()
    active = item.get("ativo", item.get("active", True))
    domain = item.get("dominio_permitido", item.get("allowed_domain", ""))
    return {
        "nome": str(name).strip() or AUTOMATION_TYPES[type_key].title(),
        "tipo": type_key,
        "token": str(token),
        "ativo": bool(active),
        "dominio_permitido": normalize_domain(domain),
        "created_at": item.get("created_at") or datetime.now().isoformat(timespec="seconds"),
        "tests": list(item.get("tests", [])),
    }


def _automation_from_row(row):
    payload = {
        "nome": row.get("nome"),
        "tipo": row.get("tipo"),
        "token": row.get("token"),
        "ativo": row.get("ativo"),
        "dominio_permitido": row.get("dominio_permitido"),
        "created_at": row.get("created_at"),
        "tests": row.get("tests") or [],
    }
    return _normalize_automation(payload)


def _load_supabase_automations():
    try:
        from .repository.supabase_client import is_configured, select_all

        if not is_configured():
            return None
        rows = select_all("master_automations", order="created_at.asc")
        items = [_automation_from_row(row) for row in rows]
        return [item for item in items if item]
    except Exception:
        return None


def _save_supabase_automations(items):
    try:
        from .repository.supabase_client import delete_rows, is_configured, select_all, upsert_row

        if not is_configured():
            return
        existing = {row.get("token"): row for row in select_all("master_automations")}
        seen = set()
        for item in items:
            token = item.get("token")
            if not token:
                continue
            seen.add(token)
            upsert_row(
                "master_automations",
                {
                    "legacy_admin_id": token,
                    "nome": item.get("nome"),
                    "tipo": item.get("tipo"),
                    "token": token,
                    "ativo": item.get("ativo", True),
                    "dominio_permitido": item.get("dominio_permitido", ""),
                    "tests": item.get("tests") or [],
                },
            )
        for token, row in existing.items():
            if token and token not in seen:
                delete_rows("master_automations", {"token": token})
    except Exception:
        pass


def ensure_automations_loaded(app):
    if hasattr(app, "automations"):
        app.automations = [_normalize_automation(item) for item in app.automations if _normalize_automation(item)]
        return
    remote = _load_supabase_automations()
    app.automations = remote if remote is not None else []


def save_automations(app):
    valid = [_normalize_automation(item) for item in getattr(app, "automations", []) if _normalize_automation(item)]
    app.automations = valid
    _save_supabase_automations(valid)
    os.makedirs(os.path.dirname(AUTOMATIONS_FILE), exist_ok=True)
    with open(AUTOMATIONS_FILE, "w", encoding="utf-8") as handle:
        json.dump(valid, handle, ensure_ascii=False, indent=2)


def start_automation_webhook_server(app):
    if getattr(app, "automation_server", None):
        return

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def _json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            token = urlparse(self.path).path.rstrip("/").split("/")[-1]
            ensure_automations_loaded(app)
            item = next((a for a in app.automations if a.get("token") == token), None)
            if not item:
                return self._json(404, {"ok": False, "error": "webhook_nao_encontrado"})
            if not item.get("ativo"):
                return self._json(403, {"ok": False, "error": "webhook_desativado"})

            allowed = normalize_domain(item.get("dominio_permitido"))
            origin = _request_origin(self.headers)
            if not allowed:
                return self._json(403, {"ok": False, "error": "dominio_nao_configurado"})
            if origin != allowed:
                return self._json(
                    403,
                    {
                        "ok": False,
                        "error": "dominio_bloqueado",
                        "allowed_domain": allowed,
                    },
                )

            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length) if length else b"{}"
            test = {
                "received_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "origin": origin,
                "body_preview": raw_body[:500].decode("utf-8", errors="replace"),
            }
            item.setdefault("tests", []).insert(0, test)
            item["tests"] = item["tests"][:20]
            save_automations(app)
            return self._json(200, {"ok": True, "tipo": item.get("tipo")})

    from .bind_host import bind_host

    server = ThreadingHTTPServer((bind_host(), AUTOMATION_PORT), Handler)
    app.automation_server = server
    threading.Thread(target=server.serve_forever, daemon=True).start()


def render_automations(parent, app):
    tk, messagebox, ttk, resolve_widget_value, setup_placeholder, render_action_buttons, COLORS, FONTS, styled_button = _lazy_ui()

    ensure_automations_loaded(app)
    start_automation_webhook_server(app)
    parent.configure(bg=COLORS["bg"])

    header = tk.Frame(parent, bg=COLORS["bg"])
    header.pack(fill="x", pady=(2, 10))
    title_box = tk.Frame(header, bg=COLORS["bg"])
    title_box.pack(side="left", fill="x", expand=True)
    tk.Label(title_box, text="Automações", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI Semibold", 18)).pack(anchor="w")
    tk.Label(
        title_box,
        text="Webhooks seguros para solicitações de transfer e cadastro de motorista.",
        bg=COLORS["bg"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
    ).pack(anchor="w")
    styled_button(header, "+ Nova automação", style="success", command=lambda: open_new_automation_modal(app)).pack(side="right")

    help_box = tk.Frame(parent, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
    help_box.pack(fill="x", pady=(0, 10))
    tk.Label(
        help_box,
        text="Tipos disponíveis: AUTOMAÇÃO SOLICITAÇÃO DE TRANSFER e AUTOMAÇÃO SOLICITAÇÃO PARA SER MOTORISTA.",
        bg=COLORS["panel_alt"],
        fg=COLORS["text"],
        font=("Segoe UI Semibold", 9),
    ).pack(anchor="w", padx=12, pady=(9, 2))
    tk.Label(
        help_box,
        text="Cada webhook só aceita POST quando estiver ativo e quando o domínio de origem for exatamente o domínio permitido.",
        bg=COLORS["panel_alt"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
    ).pack(anchor="w", padx=12, pady=(0, 9))

    bar = tk.Frame(parent, bg=COLORS["bg"])
    bar.pack(side="bottom", fill="x", pady=(8, 0))

    box = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    box.pack(fill="both", expand=True)
    if not app.automations:
        tk.Label(
            box,
            text="Nenhuma automação cadastrada. Crie um webhook de Transfer ou Motorista.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
        ).pack(pady=30)
        render_action_buttons(
            bar,
            [("Configurar Webhook", lambda: open_new_automation_modal(app), "primary")],
            bg=COLORS["bg"],
        )
        return

    columns = ("nome", "tipo", "url", "status", "dominio")
    tree = ttk.Treeview(box, columns=columns, show="headings", style="Custom.Treeview")
    headers = {
        "nome": "Nome",
        "tipo": "Tipo",
        "url": "Webhook URL",
        "status": "Status",
        "dominio": "Domínio permitido",
    }
    widths = {"nome": 190, "tipo": 260, "url": 330, "status": 90, "dominio": 220}
    for col in columns:
        tree.heading(col, text=headers[col].upper())
        tree.column(col, width=widths[col], minwidth=70, anchor="w", stretch=True)
    for item in app.automations:
        tree.insert(
            "",
            "end",
            iid=item["token"],
            values=(
                item.get("nome"),
                AUTOMATION_TYPES[item.get("tipo")],
                automation_url(item["token"]),
                "Ativo" if item.get("ativo") else "Desativado",
                item.get("dominio_permitido") or "Bloqueado até configurar",
            ),
        )
    y = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=y.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=(6, 0))
    y.grid(row=0, column=1, sticky="ns", pady=(6, 0))
    box.grid_rowconfigure(0, weight=1)
    box.grid_columnconfigure(0, weight=1)

    render_action_buttons(
        bar,
        [
            ("Configurar Webhook", lambda: configure_domain(app, tree), "primary"),
            ("Copiar URL", lambda: copy_automation_url(app, tree)),
            ("Ativar/Desativar", lambda: toggle_automation(app, tree), "secondary"),
            ("Ver testes", lambda: show_tests(app, tree), "accent"),
            ("Excluir", lambda: delete_automation(app, tree)),
        ],
        bg=COLORS["bg"],
    )


def selected_automation(app, tree):
    _tk, messagebox, *_ = _lazy_ui()
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Automações", "Selecione uma automação.", parent=app)
        return None
    return next((item for item in app.automations if item.get("token") == selected[0]), None)


def copy_automation_url(app, tree):
    _tk, messagebox, *_ = _lazy_ui()
    item = selected_automation(app, tree)
    if not item:
        return
    url = automation_url(item["token"])
    app.clipboard_clear()
    app.clipboard_append(url)
    messagebox.showinfo("Webhook copiado", url, parent=app)


def configure_domain(app, tree):
    tk, messagebox, _ttk, resolve_widget_value, setup_placeholder, _rab, COLORS, _FONTS, styled_button = _lazy_ui()
    item = selected_automation(app, tree)
    if not item:
        return
    win = tk.Toplevel(app)
    win.title("Domínio permitido")
    win.geometry("500x220")
    win.transient(app)
    win.grab_set()
    win.configure(bg=COLORS["panel"])

    tk.Label(
        win,
        text="Defina o único domínio autorizado para enviar POST para este webhook.",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        wraplength=450,
        justify="left",
    ).pack(anchor="w", padx=16, pady=(16, 6))
    tk.Label(
        win,
        text="Exemplo: https://seudominio.com. Qualquer outro domínio receberá erro 403.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=450,
        justify="left",
    ).pack(anchor="w", padx=16, pady=(0, 10))
    entry = tk.Entry(win, font=("Segoe UI", 10), bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1)
    entry.pack(fill="x", padx=16, ipady=7)
    if item.get("dominio_permitido"):
        entry.insert(0, item["dominio_permitido"])
    else:
        setup_placeholder(entry, "https://seudominio.com")

    def save_domain():
        domain = normalize_domain(resolve_widget_value(entry))
        if not domain:
            messagebox.showwarning("Domínio inválido", "Informe um domínio válido, como https://seudominio.com.", parent=win)
            return
        item["dominio_permitido"] = domain
        save_automations(app)
        win.destroy()
        app.show_page("AUTOMACOES")

    styled_button(win, "Salvar domínio", style="success", command=save_domain).pack(pady=14)


def toggle_automation(app, tree):
    item = selected_automation(app, tree)
    if not item:
        return
    item["ativo"] = not item.get("ativo", True)
    save_automations(app)
    app.show_page("AUTOMACOES")


def delete_automation(app, tree):
    _tk, messagebox, *_ = _lazy_ui()
    item = selected_automation(app, tree)
    if item and messagebox.askyesno("Excluir webhook", f"Excluir {item.get('nome')}?", parent=app):
        app.automations.remove(item)
        save_automations(app)
        app.show_page("AUTOMACOES")


def show_tests(app, tree):
    tk, _messagebox, ttk, _rwv, _sp, _rab, COLORS, _FONTS, _styled = _lazy_ui()
    item = selected_automation(app, tree)
    if not item:
        return
    win = tk.Toplevel(app)
    win.title("Testes recebidos")
    win.geometry("720x360")
    win.transient(app)
    win.configure(bg=COLORS["panel"])
    tk.Label(win, text=item.get("nome", "Webhook"), bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w", padx=12, pady=(12, 4))
    tests = item.get("tests") or []
    if not tests:
        tk.Label(win, text="Nenhum POST recebido ainda.", bg=COLORS["panel"], fg=COLORS["muted"]).pack(anchor="w", padx=12, pady=8)
        return
    cols = ("received_at", "origin", "body_preview")
    tree_tests = ttk.Treeview(win, columns=cols, show="headings", style="Custom.Treeview")
    for col, title in [("received_at", "Recebido em"), ("origin", "Origem"), ("body_preview", "Prévia do corpo")]:
        tree_tests.heading(col, text=title)
        tree_tests.column(col, width=170 if col != "body_preview" else 350, anchor="w")
    for test in tests:
        tree_tests.insert("", "end", values=(test.get("received_at"), test.get("origin"), test.get("body_preview")))
    tree_tests.pack(fill="both", expand=True, padx=12, pady=12)


def open_new_automation_modal(app):
    tk, messagebox, ttk, resolve_widget_value, setup_placeholder, _rab, COLORS, _FONTS, styled_button = _lazy_ui()
    win = tk.Toplevel(app)
    win.title("Nova Automação")
    win.geometry("520x330")
    win.transient(app)
    win.grab_set()
    win.configure(bg=COLORS["panel"])

    tk.Label(win, text="Nova Automação", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 16)).pack(anchor="w", padx=18, pady=(18, 4))
    tk.Label(win, text="Dê um nome e selecione o tipo de automação.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(0, 14))

    tk.Label(win, text="Nome da Automação", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=18, pady=(0, 4))
    name = tk.Entry(win, font=("Segoe UI", 10), bg=COLORS["input"], fg=COLORS["text"], relief="solid", bd=1)
    name.pack(fill="x", padx=18, ipady=7)
    setup_placeholder(name, "Ex: Formulário do site principal")

    tk.Label(win, text="Tipo de Automação", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=18, pady=(14, 4))
    type_var = tk.StringVar(value="")
    combo = ttk.Combobox(win, values=list(AUTOMATION_TYPES.values()), textvariable=type_var, state="readonly")
    combo.pack(fill="x", padx=18, ipady=4)
    combo.set("Selecione o tipo...")

    tk.Label(
        win,
        text="Cada automação cria um webhook próprio, com ativação individual e bloqueio por domínio permitido.",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=("Segoe UI", 9),
        wraplength=470,
        justify="left",
    ).pack(anchor="w", padx=18, pady=(12, 0))

    def create():
        automation_name = resolve_widget_value(name)
        selected_label = type_var.get()
        type_key = next((key for key, label in AUTOMATION_TYPES.items() if label == selected_label), "")
        if not automation_name:
            messagebox.showwarning("Automação", "Informe o nome da automação.", parent=win)
            return
        if not type_key:
            messagebox.showwarning("Automação", "Selecione um dos 2 tipos permitidos.", parent=win)
            return
        app.automations.append(
            {
                "nome": automation_name,
                "tipo": type_key,
                "token": secrets.token_urlsafe(TOKEN_BYTES),
                "ativo": True,
                "dominio_permitido": "",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "tests": [],
            }
        )
        save_automations(app)
        win.destroy()
        app.show_page("AUTOMACOES")

    styled_button(win, "Criar webhook", style="success", size="lg", command=create).pack(anchor="e", padx=18, pady=18)
