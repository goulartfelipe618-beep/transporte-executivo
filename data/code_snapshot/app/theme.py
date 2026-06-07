import tkinter as tk
from tkinter import ttk


COLORS = {
    "bg": "#F0F4F8",
    "panel": "#FFFFFF",
    "panel_alt": "#F8FAFC",
    "sidebar": "#1A2332",
    "sidebar_soft": "#243044",
    "sidebar_hover": "#2D3B52",
    "sidebar_active": "#2563EB",
    "sidebar_text": "#CBD5E1",
    "sidebar_muted": "#94A3B8",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "primary_soft": "#EFF6FF",
    "accent": "#6366F1",
    "text": "#0F172A",
    "muted": "#64748B",
    "line": "#E2E8F0",
    "border": "#CBD5E1",
    "white": "#FFFFFF",
    "input": "#FFFFFF",
    "warning": "#D97706",
    "warning_soft": "#FFFBEB",
    "success": "#16A34A",
    "success_dark": "#15803D",
    "success_soft": "#F0FDF4",
    "danger": "#DC2626",
    "danger_dark": "#B91C1C",
    "danger_soft": "#FEF2F2",
    "chip": "#EEF2FF",
}

FONTS = {
    "brand": ("Segoe UI Semibold", 15),
    "heading": ("Segoe UI Semibold", 14),
    "title": ("Segoe UI Semibold", 18),
    "subtitle": ("Segoe UI", 10),
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "tiny": ("Segoe UI", 8),
    "mono": ("Consolas", 10),
    "mono_lg": ("Consolas", 20, "bold"),
    "semibold_md": ("Segoe UI Semibold", 10),
    "semibold_sm": ("Segoe UI Semibold", 9),
}

ACTIVE_FONT_FAMILY = "Segoe UI"
ACTIVE_BRAND_NAME = "Nexus Transfer"

BUTTON_STYLES = {
    "primary": {"bg": COLORS["primary"], "fg": COLORS["white"], "activebackground": COLORS["primary_dark"], "activeforeground": COLORS["white"], "bd": 0, "relief": "flat", "highlightthickness": 0},
    "success": {"bg": COLORS["success"], "fg": COLORS["white"], "activebackground": COLORS["success_dark"], "activeforeground": COLORS["white"], "bd": 0, "relief": "flat", "highlightthickness": 0},
    "danger": {"bg": COLORS["danger"], "fg": COLORS["white"], "activebackground": COLORS["danger_dark"], "activeforeground": COLORS["white"], "bd": 0, "relief": "flat", "highlightthickness": 0},
    "secondary": {"bg": COLORS["panel"], "fg": COLORS["text"], "activebackground": COLORS["panel_alt"], "activeforeground": COLORS["text"], "bd": 1, "relief": "solid", "highlightthickness": 1, "highlightbackground": COLORS["border"], "highlightcolor": COLORS["border"]},
    "outline_primary": {"bg": COLORS["white"], "fg": COLORS["primary"], "activebackground": COLORS["primary_soft"], "activeforeground": COLORS["primary_dark"], "bd": 1, "relief": "solid", "highlightthickness": 1, "highlightbackground": COLORS["primary"], "highlightcolor": COLORS["primary"]},
    "outline_danger": {"bg": COLORS["white"], "fg": COLORS["danger"], "activebackground": COLORS["danger_soft"], "activeforeground": COLORS["danger_dark"], "bd": 1, "relief": "solid", "highlightthickness": 1, "highlightbackground": COLORS["danger"], "highlightcolor": COLORS["danger"]},
    "accent": {"bg": COLORS["accent"], "fg": COLORS["white"], "activebackground": "#4F46E5", "activeforeground": COLORS["white"], "bd": 0, "relief": "flat", "highlightthickness": 0},
    "warning": {"bg": COLORS["warning"], "fg": COLORS["white"], "activebackground": "#B45309", "activeforeground": COLORS["white"], "bd": 0, "relief": "flat", "highlightthickness": 0},
}


def styled_button(parent, text, style="primary", command=None, size="md", **extra):
    sizes = {
        "sm": {"padx": 8, "pady": 4, "font": FONTS["tiny"]},
        "md": {"padx": 14, "pady": 7, "font": FONTS["small"]},
        "lg": {"padx": 18, "pady": 9, "font": FONTS.get("semibold_md", ("Segoe UI Semibold", 10))},
    }
    cfg = dict(BUTTON_STYLES.get(style, BUTTON_STYLES["primary"]))
    cfg.update(sizes.get(size, sizes["md"]))
    cfg.update(extra)
    button = tk.Button(parent, text=text, cursor="hand2", command=command, **cfg)
    _bind_button_hover(button, style)
    return button


def _bind_button_hover(button, style):
    base_bg = button.cget("bg")
    hover_bg = {
        "primary": COLORS["primary_dark"],
        "success": COLORS["success_dark"],
        "danger": COLORS["danger_dark"],
        "secondary": COLORS["panel_alt"],
        "outline_primary": COLORS["primary_soft"],
        "outline_danger": COLORS["danger_soft"],
        "accent": "#4F46E5",
        "warning": "#B45309",
    }.get(style)
    if not hover_bg or hover_bg == base_bg:
        return

    button.bind("<Enter>", lambda _event: button.configure(bg=hover_bg) if button.cget("state") != "disabled" else None)
    button.bind("<Leave>", lambda _event: button.configure(bg=base_bg) if button.cget("state") != "disabled" else None)


def panel_frame(parent, **kwargs):
    bg = kwargs.pop("bg", COLORS["panel"])
    return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=COLORS["line"], **kwargs)


def badge_label(parent, text, tone="neutral"):
    tones = {
        "neutral": (COLORS["chip"], COLORS["muted"]),
        "primary": (COLORS["primary_soft"], COLORS["primary"]),
        "success": (COLORS["success_soft"], COLORS["success"]),
        "warning": (COLORS["warning_soft"], COLORS["warning"]),
        "danger": (COLORS["danger_soft"], COLORS["danger"]),
    }
    bg, fg = tones.get(tone, tones["neutral"])
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=("Consolas", 8, "bold"), padx=10, pady=5)


def configure_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "Custom.Treeview",
        background=COLORS["panel"],
        foreground=COLORS["text"],
        rowheight=32,
        fieldbackground=COLORS["panel"],
        borderwidth=0,
        relief="flat",
        font=FONTS["mono"],
    )
    style.configure(
        "Custom.Treeview.Heading",
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        relief="flat",
        borderwidth=1,
        font=FONTS.get("semibold_sm", ("Segoe UI Semibold", 9)),
    )
    style.map(
        "Custom.Treeview",
        background=[("selected", COLORS["primary_soft"])],
        foreground=[("selected", COLORS["primary_dark"])],
    )
