"""
diagnostics_view.py — IntelliNet Diagnostics View
Detailed live 8-step diagnostic probe execution table and real-time event log.
"""

import tkinter as tk
from datetime import datetime
import config as cfg
from models import DiagnosticResult


class DiagnosticsView(tk.Frame):
    """
    Dedicated Diagnostics Page:
      - 8-row live diagnostic table with step pills, badges, and detailed outputs.
      - Real-time diagnostic console log displaying timestamped events.
    """

    STEPS_DEF = [
        ("01", "Network Adapter", "Detects physical or wireless interface state and speed via psutil"),
        ("02", "IPv4 Address", "Checks valid IP assignment and detects APIPA/self-assigned ranges"),
        ("03", "Default Gateway", "Checks gateway route and ICMP ping response from local router"),
        ("04", "Wi-Fi / Link Info", "Queries netsh wlan for SSID, BSSID, Signal %, channel and rates"),
        ("05", "DNS Resolution", "Tests the configured DNS resolver with a bounded lookup"),
        ("06", "Internet Connectivity", "Tests public network reachability using ICMP and TCP fallback"),
        ("07", "Latency & Jitter", "Measures average, min, max round-trip time and jitter"),
        ("08", "Packet Loss", "Calculates packet loss percentage across multi-ping sequence"),
    ]

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self.row_widgets = []
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # ── Table Card ────────────────────────────────────────────────
        table_card = tk.Frame(
            container,
            bg=cfg.COLOR_PANEL,
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        table_card.pack(fill="x", pady=(0, 14))

        # Table Header
        header = tk.Frame(table_card, bg=cfg.COLOR_PANEL_DARK, pady=8, padx=12)
        header.pack(fill="x", pady=(0, 6))

        tk.Label(
            header, text="STEP", font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_MUTED, width=6, anchor="w"
        ).pack(side="left")

        tk.Label(
            header, text="DIAGNOSTIC PROBE", font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_MUTED, width=28, anchor="w"
        ).pack(side="left")

        tk.Label(
            header, text="STATUS", font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_MUTED, width=12, anchor="w"
        ).pack(side="left")

        tk.Label(
            header, text="MEASURED VALUE / DETAILS", font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_MUTED, anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # 8 Rows
        for i, (num, title, desc) in enumerate(self.STEPS_DEF):
            row_bg = cfg.COLOR_PANEL if i % 2 == 0 else "#192231"
            row = tk.Frame(table_card, bg=row_bg, pady=7, padx=12)
            row.pack(fill="x", pady=1)

            # Step Pill
            pill = tk.Label(
                row,
                text=num,
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_TEXT_MUTED,
                width=4,
                padx=2,
                pady=1,
            )
            pill.pack(side="left", padx=(0, 12))

            # Title
            title_lbl = tk.Label(
                row,
                text=title,
                font=("Segoe UI", 9, "bold"),
                bg=row_bg,
                fg=cfg.COLOR_TEXT_PRIMARY,
                width=24,
                anchor="w",
            )
            title_lbl.pack(side="left")

            # Status Badge
            badge = tk.Label(
                row,
                text="PENDING",
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_TEXT_MUTED,
                width=10,
                padx=4,
                pady=1,
            )
            badge.pack(side="left", padx=(0, 12))

            # Details
            detail_lbl = tk.Label(
                row,
                text="Awaiting diagnostic scan...",
                font=("Segoe UI", 8),
                bg=row_bg,
                fg=cfg.COLOR_TEXT_MUTED,
                anchor="w",
            )
            detail_lbl.pack(side="left", fill="x", expand=True)

            self.row_widgets.append({
                "frame": row,
                "pill": pill,
                "badge": badge,
                "detail": detail_lbl,
                "bg": row_bg,
            })

        # ── Console Log Card ──────────────────────────────────────────
        log_card = tk.Frame(
            container,
            bg=cfg.COLOR_PANEL,
            padx=16,
            pady=12,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        log_card.pack(fill="both", expand=True)

        log_head = tk.Frame(log_card, bg=cfg.COLOR_PANEL)
        log_head.pack(fill="x", pady=(0, 8))

        tk.Label(
            log_head,
            text="LIVE DIAGNOSTIC EXECUTION CONSOLE",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.log_count = tk.Label(
            log_head,
            text="0 events recorded",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        )
        self.log_count.pack(side="right")

        # Monospaced text box
        self.console = tk.Text(
            log_card,
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_TEXT_PRIMARY,
            insertbackground=cfg.COLOR_ACCENT,
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
            height=7,
            wrap="word",
        )
        self.console.pack(fill="both", expand=True)
        self.console.config(state="disabled")

        # Initial console message
        self.append_log("IntelliNet diagnostic engine initialized and ready.")

    def reset_table(self):
        """Reset all table rows to pending state."""
        for i, row in enumerate(self.row_widgets):
            row["badge"].config(
                text="PENDING",
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_TEXT_MUTED,
            )
            row["detail"].config(
                text="Awaiting diagnostic scan...",
                fg=cfg.COLOR_TEXT_MUTED,
            )
            row["pill"].config(bg=cfg.COLOR_PANEL_ALT, fg=cfg.COLOR_TEXT_MUTED)

    def set_row_testing(self, row_idx: int):
        """Mark a row as actively running."""
        if 0 <= row_idx < len(self.row_widgets):
            r = self.row_widgets[row_idx]
            r["badge"].config(
                text="TESTING...",
                bg="#0284C7",
                fg="#FFFFFF",
            )
            r["pill"].config(bg=cfg.COLOR_ACCENT, fg="#FFFFFF")
            r["detail"].config(text="Querying network interface...", fg=cfg.COLOR_ACCENT)

    def set_row_result(self, row_idx: int, symbol: str, details: str, tag: str):
        """Update a row with live results (pass/fail/warn/info)."""
        if 0 <= row_idx < len(self.row_widgets):
            r = self.row_widgets[row_idx]

            if tag == "pass":
                bg_col = cfg.COLOR_SUCCESS
                fg_col = "#0F172A"
                text   = f"PASS  {symbol}"
            elif tag == "fail":
                bg_col = cfg.COLOR_FAILURE
                fg_col = "#FFFFFF"
                text   = f"FAIL  {symbol}"
            elif tag == "warn":
                bg_col = cfg.COLOR_WARNING
                fg_col = "#0F172A"
                text   = f"WARN  {symbol}"
            elif tag == "info" or tag == "muted":
                bg_col = cfg.COLOR_PANEL_ALT
                fg_col = cfg.COLOR_ACCENT
                text   = f"INFO  {symbol}"
            else:
                bg_col = cfg.COLOR_PANEL_ALT
                fg_col = cfg.COLOR_TEXT_PRIMARY
                text   = symbol

            r["badge"].config(text=text, bg=bg_col, fg=fg_col)
            r["detail"].config(text=details, fg=cfg.COLOR_TEXT_PRIMARY)
            r["pill"].config(bg=bg_col, fg=fg_col)

    def append_log(self, message: str):
        """Append a timestamped message to the live diagnostic console."""
        now = datetime.now().strftime("%H:%M:%S")
        line = f"[{now}] {message}\n"

        self.console.config(state="normal")
        self.console.insert("end", line)
        self.console.see("end")
        line_count = max(0, int(self.console.index("end-1c").split(".")[0]) - 1)
        excess = line_count - cfg.MAX_DIAGNOSTIC_LOG_LINES
        if excess > 0:
            self.console.delete("1.0", f"{excess + 1}.0")
        self.console.config(state="disabled")

        # Update event counter
        lines = max(0, int(self.console.index("end-1c").split(".")[0]) - 1)
        self.log_count.config(text=f"{lines} events recorded")

    def update_data(self, result: DiagnosticResult):
        """Final synchronization from a completed DiagnosticResult."""
        pass  # Rows are already updated in real time by the worker loop
