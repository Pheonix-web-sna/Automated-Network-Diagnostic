"""
monitoring_view.py — IntelliNet Monitoring View (Phase 3)

Live network monitoring dashboard:
  - Start / Stop monitoring controls
  - Configurable scan interval
  - Live event log display
  - Degradation alert panel
  - Monitoring statistics
  - Real-time status indicators
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import config as cfg
from models import DiagnosticResult


class MonitoringView(tk.Frame):
    """
    Monitoring page for continuous background network observation.
    Controls Start/Stop of the monitoring thread and displays
    live event log and degradation alerts.
    """

    def __init__(self, parent, on_start_monitor=None, on_stop_monitor=None, **kw):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self.on_start_monitor = on_start_monitor
        self.on_stop_monitor = on_stop_monitor
        self.is_monitoring = False
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # ═══════════════════════════════════════════════════════════════
        # TOP ROW: CONTROL PANEL + STATS
        # ═══════════════════════════════════════════════════════════════
        top_row = tk.Frame(container, bg=cfg.COLOR_BG)
        top_row.pack(fill="x", pady=(0, 14))
        top_row.columnconfigure(0, weight=5)
        top_row.columnconfigure(1, weight=5)

        # ── Control Card ─────────────────────────────────────────────
        ctrl_card = tk.Frame(
            top_row, bg=cfg.COLOR_PANEL, padx=18, pady=16,
            highlightthickness=1, highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        ctrl_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctrl_head = tk.Frame(ctrl_card, bg=cfg.COLOR_PANEL)
        ctrl_head.pack(fill="x")

        tk.Label(
            ctrl_head, text="NETWORK MONITORING CONTROLS",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.monitor_badge = tk.Label(
            ctrl_head, text="STOPPED",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_ALT, fg=cfg.COLOR_TEXT_MUTED,
            padx=8, pady=2,
        )
        self.monitor_badge.pack(side="right")

        # Status indicator
        status_row = tk.Frame(ctrl_card, bg=cfg.COLOR_PANEL)
        status_row.pack(fill="x", pady=(12, 8))

        self.status_dot = tk.Label(
            status_row, text="●", font=("Segoe UI", 14),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        )
        self.status_dot.pack(side="left", padx=(0, 8))

        self.status_text = tk.Label(
            status_row, text="Monitoring is not active",
            font=("Segoe UI", 11, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_PRIMARY,
        )
        self.status_text.pack(side="left")

        # Interval setting
        interval_row = tk.Frame(ctrl_card, bg=cfg.COLOR_PANEL)
        interval_row.pack(fill="x", pady=(4, 10))

        tk.Label(
            interval_row, text="Scan Interval:",
            font=("Segoe UI", 9),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.interval_var = tk.StringVar(value="60")
        interval_combo = ttk.Combobox(
            interval_row,
            textvariable=self.interval_var,
            values=["30", "60", "120", "300", "600"],
            state="readonly",
            width=6,
        )
        interval_combo.pack(side="left", padx=(8, 4))

        tk.Label(
            interval_row, text="seconds",
            font=("Segoe UI", 9),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        # Start / Stop Buttons
        btn_row = tk.Frame(ctrl_card, bg=cfg.COLOR_PANEL)
        btn_row.pack(fill="x")

        self.btn_start = tk.Button(
            btn_row, text="▶  Start Monitoring",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_SUCCESS, fg="#FFFFFF",
            activebackground="#16A34A", activeforeground="#FFFFFF",
            relief="flat", cursor="hand2",
            command=self._on_start,
            padx=16, pady=7,
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = tk.Button(
            btn_row, text="⏹  Stop Monitoring",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_FAILURE, fg="#FFFFFF",
            activebackground="#DC2626", activeforeground="#FFFFFF",
            relief="flat", cursor="hand2",
            command=self._on_stop,
            padx=16, pady=7,
            state="disabled",
        )
        self.btn_stop.pack(side="left")

        # ── Stats Card ───────────────────────────────────────────────
        stats_card = tk.Frame(
            top_row, bg=cfg.COLOR_PANEL, padx=18, pady=16,
            highlightthickness=1, highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        stats_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tk.Label(
            stats_card, text="MONITORING STATISTICS",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        stats_grid = tk.Frame(stats_card, bg=cfg.COLOR_PANEL)
        stats_grid.pack(fill="both", expand=True, pady=(10, 0))
        for i in range(2):
            stats_grid.columnconfigure(i, weight=1)

        self.lbl_scans = self._mini_stat(stats_grid, 0, 0, "Scans Completed", "0")
        self.lbl_alerts = self._mini_stat(stats_grid, 0, 1, "Alerts Triggered", "0")
        self.lbl_last_scan = self._mini_stat(stats_grid, 1, 0, "Last Scan Time", "—")
        self.lbl_next_scan = self._mini_stat(stats_grid, 1, 1, "Next Scan In", "—")

        # ═══════════════════════════════════════════════════════════════
        # DEGRADATION ALERTS PANEL
        # ═══════════════════════════════════════════════════════════════
        alert_card = tk.Frame(
            container, bg=cfg.COLOR_PANEL, padx=16, pady=12,
            highlightthickness=1, highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        alert_card.pack(fill="x", pady=(0, 14))

        alert_head = tk.Frame(alert_card, bg=cfg.COLOR_PANEL)
        alert_head.pack(fill="x", pady=(0, 6))

        tk.Label(
            alert_head, text="⚠  DEGRADATION ALERTS",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_WARNING,
        ).pack(side="left")

        self.alert_count_lbl = tk.Label(
            alert_head, text="No alerts",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        )
        self.alert_count_lbl.pack(side="right")

        self.alert_container = tk.Frame(alert_card, bg=cfg.COLOR_PANEL)
        self.alert_container.pack(fill="x")

        self.no_alerts_lbl = tk.Label(
            self.alert_container,
            text="No degradation alerts. Network is stable.",
            font=("Segoe UI", 9),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_SUCCESS,
        )
        self.no_alerts_lbl.pack(fill="x")

        # ═══════════════════════════════════════════════════════════════
        # EVENT LOG
        # ═══════════════════════════════════════════════════════════════
        log_card = tk.Frame(
            container, bg=cfg.COLOR_PANEL, padx=16, pady=12,
            highlightthickness=1, highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        log_card.pack(fill="both", expand=True)

        log_head = tk.Frame(log_card, bg=cfg.COLOR_PANEL)
        log_head.pack(fill="x", pady=(0, 8))

        tk.Label(
            log_head, text="NETWORK EVENT LOG",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.event_count_lbl = tk.Label(
            log_head, text="0 events",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        )
        self.event_count_lbl.pack(side="right")

        self.event_text = tk.Text(
            log_card,
            bg=cfg.COLOR_PANEL_DARK,
            fg=cfg.COLOR_TEXT_PRIMARY,
            insertbackground=cfg.COLOR_ACCENT,
            font=("Consolas", 9),
            relief="flat",
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
            height=12,
            wrap="word",
        )
        self.event_text.pack(fill="both", expand=True)
        self.event_text.config(state="disabled")

        # Color tags for event log
        self.event_text.tag_config("info", foreground=cfg.COLOR_ACCENT)
        self.event_text.tag_config("warning", foreground=cfg.COLOR_WARNING)
        self.event_text.tag_config("critical", foreground=cfg.COLOR_FAILURE)
        self.event_text.tag_config("success", foreground=cfg.COLOR_SUCCESS)
        self.event_text.tag_config("degradation", foreground="#F97316")

        # Load initial event log
        self._refresh_event_log()

    def _mini_stat(self, parent, row, col, label, default_val) -> tk.Label:
        """Create a small stat display in a grid."""
        frame = tk.Frame(parent, bg=cfg.COLOR_PANEL_DARK, padx=10, pady=8)
        frame.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)

        tk.Label(
            frame, text=label, font=("Segoe UI", 7, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        val_lbl = tk.Label(
            frame, text=default_val, font=("Segoe UI", 11, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_PRIMARY,
        )
        val_lbl.pack(anchor="w")
        return val_lbl

    def _on_start(self):
        """Handle Start Monitoring button click."""
        interval = int(self.interval_var.get())
        self.set_monitoring_state(True)
        if self.on_start_monitor:
            self.on_start_monitor(interval)

    def _on_stop(self):
        """Handle Stop Monitoring button click."""
        self.set_monitoring_state(False)
        if self.on_stop_monitor:
            self.on_stop_monitor()

    def set_monitoring_state(self, is_active: bool):
        """Update UI to reflect monitoring state."""
        self.is_monitoring = is_active
        if is_active:
            self.monitor_badge.config(text="ACTIVE", bg=cfg.COLOR_SUCCESS, fg="#0F172A")
            self.status_dot.config(fg=cfg.COLOR_SUCCESS)
            self.status_text.config(text="Monitoring is active", fg=cfg.COLOR_SUCCESS)
            self.btn_start.config(state="disabled", bg=cfg.COLOR_PANEL_ALT)
            self.btn_stop.config(state="normal", bg=cfg.COLOR_FAILURE)
        else:
            self.monitor_badge.config(text="STOPPED", bg=cfg.COLOR_PANEL_ALT, fg=cfg.COLOR_TEXT_MUTED)
            self.status_dot.config(fg=cfg.COLOR_TEXT_MUTED)
            self.status_text.config(text="Monitoring is not active", fg=cfg.COLOR_TEXT_PRIMARY)
            self.btn_start.config(state="normal", bg=cfg.COLOR_SUCCESS)
            self.btn_stop.config(state="disabled", bg=cfg.COLOR_PANEL_ALT)
            self.lbl_next_scan.config(text="—")

    def update_scan_count(self, count: int):
        """Update the scans completed counter."""
        self.lbl_scans.config(text=str(count))

    def update_alert_count(self, count: int):
        """Update the alerts triggered counter."""
        self.lbl_alerts.config(text=str(count), fg=cfg.COLOR_WARNING if count > 0 else cfg.COLOR_TEXT_PRIMARY)

    def update_last_scan_time(self, ts: str):
        """Update the last scan time label."""
        self.lbl_last_scan.config(text=ts)

    def update_next_scan(self, seconds: int):
        """Update countdown to next scan."""
        if seconds <= 0:
            self.lbl_next_scan.config(text="Now...")
        elif seconds < 60:
            self.lbl_next_scan.config(text=f"{seconds}s")
        else:
            m = seconds // 60
            s = seconds % 60
            self.lbl_next_scan.config(text=f"{m}m {s}s")

    def show_alerts(self, alerts: list):
        """Display degradation alerts in the alert panel."""
        # Clear existing alerts
        for w in self.alert_container.winfo_children():
            w.destroy()

        if not alerts:
            lbl = tk.Label(
                self.alert_container,
                text="✓  No degradation alerts. Network is stable.",
                font=("Segoe UI", 9),
                bg=cfg.COLOR_PANEL, fg=cfg.COLOR_SUCCESS,
            )
            lbl.pack(fill="x")
            self.alert_count_lbl.config(text="No alerts", fg=cfg.COLOR_SUCCESS)
        else:
            self.alert_count_lbl.config(text=f"{len(alerts)} alert(s)", fg=cfg.COLOR_WARNING)
            for alert_msg in alerts:
                alert_frame = tk.Frame(
                    self.alert_container, bg="#1C1710",
                    padx=10, pady=6,
                    highlightthickness=1,
                    highlightbackground=cfg.COLOR_WARNING,
                )
                alert_frame.pack(fill="x", pady=2)

                tk.Label(
                    alert_frame, text="⚠",
                    font=("Segoe UI", 10),
                    bg="#1C1710", fg=cfg.COLOR_WARNING,
                ).pack(side="left", padx=(0, 8))

                tk.Label(
                    alert_frame, text=alert_msg,
                    font=("Segoe UI", 8),
                    bg="#1C1710", fg=cfg.COLOR_WARNING,
                    anchor="w", wraplength=700,
                    justify="left",
                ).pack(side="left", fill="x", expand=True)

    def append_event(self, message: str, severity: str = "INFO"):
        """Add a timestamped event to the log display."""
        now = datetime.now().strftime("%H:%M:%S")
        tag = severity.lower()
        if tag not in ("info", "warning", "critical", "success", "degradation"):
            tag = "info"

        prefix = {
            "info": "ℹ",
            "warning": "⚠",
            "critical": "✗",
            "success": "✓",
            "degradation": "▼",
        }.get(tag, "●")

        line = f"[{now}] {prefix}  {message}\n"

        self.event_text.config(state="normal")
        self.event_text.insert("end", line, tag)
        self.event_text.see("end")
        self.event_text.config(state="disabled")

        # Update count
        lines = int(self.event_text.index("end-1c").split(".")[0])
        self.event_count_lbl.config(text=f"{lines} events")

    def _refresh_event_log(self):
        """Load recent events from database."""
        try:
            import db_manager as db
            events = db.get_event_log(limit=100)

            self.event_text.config(state="normal")
            self.event_text.delete("1.0", "end")

            if not events:
                self.event_text.insert("end", "No events recorded yet. Start monitoring to begin.\n", "info")
            else:
                for evt in reversed(events):  # Show oldest first
                    ts = evt.get("timestamp", "")
                    sev = evt.get("severity", "INFO").lower()
                    msg = evt.get("message", "")
                    tag = sev if sev in ("info", "warning", "critical", "success", "degradation") else "info"
                    self.event_text.insert("end", f"[{ts}] {msg}\n", tag)

            self.event_text.see("end")
            self.event_text.config(state="disabled")

            count = db.get_event_count()
            self.event_count_lbl.config(text=f"{count} events")

        except Exception:
            pass

    def update_data(self, result: DiagnosticResult):
        """Called after each diagnostic — refresh event log."""
        self._refresh_event_log()
