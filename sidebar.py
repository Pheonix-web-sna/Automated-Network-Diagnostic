"""
sidebar.py — IntelliNet Navigation Sidebar
Professional sidebar for switching between IntelliNet views.
"""

import tkinter as tk
from typing import Callable, Dict
import config as cfg


class Sidebar(tk.Frame):
    """
    Vertical sidebar containing branding, navigation tabs,
    and a persistent connection status footer.
    """

    NAV_ITEMS = [
        ("dashboard", "📊  Dashboard"),
        ("diagnostics", "🔍  Diagnostics"),
        ("network_info", "🌐  Network Info"),
        ("performance", "⚡  Performance"),
        ("recommendations", "💡  Recommendations"),
        ("history", "📈  History"),
        ("monitoring", "🛡  Monitoring"),
    ]

    def __init__(self, parent, on_navigate: Callable[[str], None], **kw):
        super().__init__(parent, bg=cfg.COLOR_SIDEBAR, width=220, **kw)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.active_page = "dashboard"
        self.nav_buttons: Dict[str, tk.Frame] = {}
        self.nav_labels: Dict[str, tk.Label] = {}
        self.indicator_bars: Dict[str, tk.Frame] = {}

        self._build_ui()

    def _build_ui(self):
        # ── Top Branding Section ──────────────────────────────────────────
        brand_frame = tk.Frame(self, bg=cfg.COLOR_SIDEBAR, pady=18, padx=16)
        brand_frame.pack(fill="x")

        # App Logo & Title
        title_row = tk.Frame(brand_frame, bg=cfg.COLOR_SIDEBAR)
        title_row.pack(fill="x", anchor="w")

        icon_lbl = tk.Label(
            title_row,
            text="⚡",
            font=("Segoe UI", 16, "bold"),
            bg=cfg.COLOR_SIDEBAR,
            fg=cfg.COLOR_ACCENT,
        )
        icon_lbl.pack(side="left", padx=(0, 6))

        title_lbl = tk.Label(
            title_row,
            text="INTELLINET",
            font=("Segoe UI", 14, "bold"),
            bg=cfg.COLOR_SIDEBAR,
            fg=cfg.COLOR_TEXT_PRIMARY,
        )
        title_lbl.pack(side="left")

        ver_badge = tk.Label(
            title_row,
            text="PRO",
            font=("Segoe UI", 7, "bold"),
            bg=cfg.COLOR_ACCENT,
            fg="#FFFFFF",
            padx=4,
            pady=1,
        )
        ver_badge.pack(side="left", padx=(6, 0))

        sub_lbl = tk.Label(
            brand_frame,
            text="Network Health & Diagnostics",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_SIDEBAR,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
        )
        sub_lbl.pack(fill="x", pady=(3, 0))

        # Thin divider
        div = tk.Frame(self, bg=cfg.COLOR_PANEL, height=1)
        div.pack(fill="x", padx=12, pady=(0, 14))

        # ── Navigation Buttons ──────────────────────────────────────────
        nav_container = tk.Frame(self, bg=cfg.COLOR_SIDEBAR)
        nav_container.pack(fill="x", expand=True, anchor="n")

        for page_id, label_text in self.NAV_ITEMS:
            btn_frame = tk.Frame(nav_container, bg=cfg.COLOR_SIDEBAR, cursor="hand2")
            btn_frame.pack(fill="x", pady=2, padx=8)

            # Left accent indicator bar (hidden by default)
            indicator = tk.Frame(btn_frame, bg=cfg.COLOR_SIDEBAR, width=3)
            indicator.pack(side="left", fill="y")
            self.indicator_bars[page_id] = indicator

            # Nav text label
            lbl = tk.Label(
                btn_frame,
                text=f"  {label_text}",
                font=("Segoe UI", 10),
                bg=cfg.COLOR_SIDEBAR,
                fg=cfg.COLOR_TEXT_MUTED,
                anchor="w",
                pady=9,
                padx=6,
                cursor="hand2",
            )
            lbl.pack(side="left", fill="x", expand=True)

            self.nav_buttons[page_id] = btn_frame
            self.nav_labels[page_id] = lbl

            # Bind events for clicking and hover
            for widget in (btn_frame, lbl):
                widget.bind("<Button-1>", lambda e, pid=page_id: self._on_click(pid))
                widget.bind("<Enter>", lambda e, pid=page_id: self._on_hover(pid, True))
                widget.bind("<Leave>", lambda e, pid=page_id: self._on_hover(pid, False))

        # ── Bottom System Status Card ──────────────────────────────────
        footer = tk.Frame(self, bg=cfg.COLOR_SIDEBAR, padx=12, pady=16)
        footer.pack(side="bottom", fill="x")

        status_card = tk.Frame(
            footer,
            bg=cfg.COLOR_PANEL_DARK,
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL,
        )
        status_card.pack(fill="x")

        status_header = tk.Frame(status_card, bg=cfg.COLOR_PANEL_DARK)
        status_header.pack(fill="x")

        self.footer_dot = tk.Label(
            status_header,
            text="●",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_SUCCESS,
        )
        self.footer_dot.pack(side="left", padx=(0, 4))

        self.footer_status = tk.Label(
            status_header,
            text="SYSTEM READY",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_SUCCESS,
        )
        self.footer_status.pack(side="left")

        self.footer_adapter = tk.Label(
            status_card,
            text="Adapter: Detecting...",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.footer_adapter.pack(fill="x", pady=(4, 0))

        ver_lbl = tk.Label(
            footer,
            text=f"IntelliNet v{cfg.APP_VERSION}",
            font=("Segoe UI", 7),
            bg=cfg.COLOR_SIDEBAR,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="center",
        )
        ver_lbl.pack(pady=(8, 0))

        # Set default active item
        self.set_active("dashboard")

    def _on_click(self, page_id: str):
        if page_id != self.active_page:
            self.set_active(page_id)
            self.on_navigate(page_id)

    def _on_hover(self, page_id: str, is_hover: bool):
        if page_id == self.active_page:
            return
        btn_frame = self.nav_buttons[page_id]
        lbl = self.nav_labels[page_id]
        if is_hover:
            btn_frame.config(bg="#131C2E")
            lbl.config(bg="#131C2E", fg=cfg.COLOR_TEXT_PRIMARY)
        else:
            btn_frame.config(bg=cfg.COLOR_SIDEBAR)
            lbl.config(bg=cfg.COLOR_SIDEBAR, fg=cfg.COLOR_TEXT_MUTED)

    def set_active(self, page_id: str):
        """Update active button styling."""
        self.active_page = page_id
        for pid, btn_frame in self.nav_buttons.items():
            lbl = self.nav_labels[pid]
            ind = self.indicator_bars[pid]
            if pid == page_id:
                btn_frame.config(bg=cfg.COLOR_SIDEBAR_ACTIVE)
                lbl.config(
                    bg=cfg.COLOR_SIDEBAR_ACTIVE,
                    fg=cfg.COLOR_ACCENT,
                    font=("Segoe UI", 10, "bold"),
                )
                ind.config(bg=cfg.COLOR_ACCENT)
            else:
                btn_frame.config(bg=cfg.COLOR_SIDEBAR)
                lbl.config(
                    bg=cfg.COLOR_SIDEBAR,
                    fg=cfg.COLOR_TEXT_MUTED,
                    font=("Segoe UI", 10),
                )
                ind.config(bg=cfg.COLOR_SIDEBAR)

    def update_status(self, adapter_name: str, is_running: bool, is_healthy: bool):
        """Update the footer indicator with live system state."""
        if is_running:
            self.footer_dot.config(fg=cfg.COLOR_WARNING)
            self.footer_status.config(text="SCANNING...", fg=cfg.COLOR_WARNING)
        elif is_healthy:
            self.footer_dot.config(fg=cfg.COLOR_SUCCESS)
            self.footer_status.config(text="HEALTHY", fg=cfg.COLOR_SUCCESS)
        else:
            self.footer_dot.config(fg=cfg.COLOR_FAILURE)
            self.footer_status.config(text="ATTENTION", fg=cfg.COLOR_FAILURE)

        disp = adapter_name if adapter_name and adapter_name != "None" else "No Adapter"
        self.footer_adapter.config(text=f"Adapter: {disp}")
