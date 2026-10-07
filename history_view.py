"""
history_view.py — IntelliNet History View (Phase 3)

Displays historical diagnostic data with matplotlib charts:
  - Health Score trend line
  - Latency trend with min/max bands
  - Packet Loss bar chart
  - DNS status timeline
  - Session history table
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import config as cfg
from models import DiagnosticResult

# matplotlib with Tkinter backend
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates


class HistoryView(tk.Frame):
    """
    History page with embedded matplotlib charts and session table.
    Charts auto-refresh when update_data() is called.
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self._build_ui()
        self._load_history()

    def _build_ui(self):
        # Scrollable container
        canvas_scroll = tk.Canvas(self, bg=cfg.COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas_scroll.yview)
        self.scroll_frame = tk.Frame(canvas_scroll, bg=cfg.COLOR_BG)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")),
        )

        canvas_scroll.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel, add="+")

        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._canvas_scroll = canvas_scroll

        container = self.scroll_frame
        pad_kw = dict(padx=24, pady=(8, 0))

        # ═══════════════════════════════════════════════════════════════
        # SUMMARY STATS ROW
        # ═══════════════════════════════════════════════════════════════
        stats_row = tk.Frame(container, bg=cfg.COLOR_BG)
        stats_row.pack(fill="x", **pad_kw)
        for i in range(4):
            stats_row.columnconfigure(i, weight=1)

        self.stat_sessions = self._stat_card(stats_row, 0, "TOTAL SESSIONS", "0", cfg.COLOR_ACCENT)
        self.stat_avg_health = self._stat_card(stats_row, 1, "AVG HEALTH SCORE", "—", cfg.COLOR_SUCCESS)
        self.stat_avg_latency = self._stat_card(stats_row, 2, "AVG LATENCY", "— ms", cfg.COLOR_TEAL)
        self.stat_uptime = self._stat_card(stats_row, 3, "DNS SUCCESS RATE", "— %", cfg.COLOR_PURPLE)

        # ═══════════════════════════════════════════════════════════════
        # CHARTS ROW 1: Health Score + Latency
        # ═══════════════════════════════════════════════════════════════
        charts_row1 = tk.Frame(container, bg=cfg.COLOR_BG)
        charts_row1.pack(fill="x", padx=24, pady=(12, 0))
        charts_row1.columnconfigure(0, weight=1)
        charts_row1.columnconfigure(1, weight=1)

        # Health Score Chart
        health_card = self._chart_card(charts_row1, 0, "HEALTH SCORE TREND")
        self.health_fig = Figure(figsize=(5, 2.2), dpi=100, facecolor=cfg.COLOR_PANEL)
        self.health_ax = self.health_fig.add_subplot(111)
        self._style_axis(self.health_ax)
        self.health_canvas = FigureCanvasTkAgg(self.health_fig, master=health_card)
        self.health_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Latency Chart
        latency_card = self._chart_card(charts_row1, 1, "LATENCY TREND (ms)")
        self.latency_fig = Figure(figsize=(5, 2.2), dpi=100, facecolor=cfg.COLOR_PANEL)
        self.latency_ax = self.latency_fig.add_subplot(111)
        self._style_axis(self.latency_ax)
        self.latency_canvas = FigureCanvasTkAgg(self.latency_fig, master=latency_card)
        self.latency_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # ═══════════════════════════════════════════════════════════════
        # CHARTS ROW 2: Packet Loss + DNS Status
        # ═══════════════════════════════════════════════════════════════
        charts_row2 = tk.Frame(container, bg=cfg.COLOR_BG)
        charts_row2.pack(fill="x", padx=24, pady=(12, 0))
        charts_row2.columnconfigure(0, weight=1)
        charts_row2.columnconfigure(1, weight=1)

        # Packet Loss Chart
        loss_card = self._chart_card(charts_row2, 0, "PACKET LOSS HISTORY (%)")
        self.loss_fig = Figure(figsize=(5, 2.2), dpi=100, facecolor=cfg.COLOR_PANEL)
        self.loss_ax = self.loss_fig.add_subplot(111)
        self._style_axis(self.loss_ax)
        self.loss_canvas = FigureCanvasTkAgg(self.loss_fig, master=loss_card)
        self.loss_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # DNS Status Chart
        dns_card = self._chart_card(charts_row2, 1, "DNS RESOLUTION STATUS")
        self.dns_fig = Figure(figsize=(5, 2.2), dpi=100, facecolor=cfg.COLOR_PANEL)
        self.dns_ax = self.dns_fig.add_subplot(111)
        self._style_axis(self.dns_ax)
        self.dns_canvas = FigureCanvasTkAgg(self.dns_fig, master=dns_card)
        self.dns_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # ═══════════════════════════════════════════════════════════════
        # SESSION HISTORY TABLE
        # ═══════════════════════════════════════════════════════════════
        table_card = tk.Frame(
            container,
            bg=cfg.COLOR_PANEL,
            padx=16, pady=14,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        table_card.pack(fill="x", padx=24, pady=(12, 16))

        table_header = tk.Frame(table_card, bg=cfg.COLOR_PANEL)
        table_header.pack(fill="x", pady=(0, 8))

        tk.Label(
            table_header, text="DIAGNOSTIC SESSION HISTORY",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.lbl_table_count = tk.Label(
            table_header, text="0 sessions",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        )
        self.lbl_table_count.pack(side="right")

        # Table columns
        columns = ("time", "health", "status", "latency", "loss", "dns", "adapter")
        self.tree = ttk.Treeview(
            table_card, columns=columns, show="headings", height=8,
            selectmode="browse",
        )

        col_config = [
            ("time", "Timestamp", 140),
            ("health", "Health", 60),
            ("status", "RCA Status", 180),
            ("latency", "Latency", 75),
            ("loss", "Loss %", 60),
            ("dns", "DNS", 55),
            ("adapter", "Adapter", 100),
        ]
        for cid, heading, width in col_config:
            self.tree.heading(cid, text=heading, anchor="w")
            self.tree.column(cid, width=width, minwidth=40, anchor="w")

        # Treeview styling
        style = ttk.Style()
        style.configure(
            "History.Treeview",
            background=cfg.COLOR_PANEL_DARK,
            foreground=cfg.COLOR_TEXT_PRIMARY,
            fieldbackground=cfg.COLOR_PANEL_DARK,
            rowheight=24,
            font=("Segoe UI", 8),
        )
        style.configure(
            "History.Treeview.Heading",
            background=cfg.COLOR_PANEL,
            foreground=cfg.COLOR_TEXT_MUTED,
            font=("Segoe UI", 8, "bold"),
        )
        self.tree.configure(style="History.Treeview")

        tree_scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

    def _stat_card(self, parent, col, title, default_val, color) -> dict:
        """Mini stat card for summary row."""
        card = tk.Frame(
            parent, bg=cfg.COLOR_PANEL, padx=14, pady=10,
            highlightthickness=1, highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        card.grid(row=0, column=col, sticky="nsew", padx=4)

        tk.Label(
            card, text=title, font=("Segoe UI", 7, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(fill="x")

        val_lbl = tk.Label(
            card, text=default_val, font=("Segoe UI", 16, "bold"),
            bg=cfg.COLOR_PANEL, fg=color,
        )
        val_lbl.pack(fill="x", pady=(2, 0))

        return {"val": val_lbl}

    def _chart_card(self, parent, col, title) -> tk.Frame:
        """Card wrapper for a chart."""
        card = tk.Frame(
            parent, bg=cfg.COLOR_PANEL, padx=12, pady=10,
            highlightthickness=1, highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        card.grid(row=0, column=col, sticky="nsew", padx=4)

        tk.Label(
            card, text=title, font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 4))

        return card

    def _style_axis(self, ax):
        """Apply dark theme to matplotlib axis."""
        ax.set_facecolor(cfg.COLOR_PANEL_DARK)
        ax.tick_params(colors=cfg.COLOR_TEXT_MUTED, labelsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(cfg.COLOR_PANEL_ALT)
        ax.spines["left"].set_color(cfg.COLOR_PANEL_ALT)
        ax.grid(True, alpha=0.15, color=cfg.COLOR_TEXT_MUTED)

    def _load_history(self):
        """Load historical data from database and render charts."""
        try:
            import db_manager as db

            # Summary stats
            session_count = db.get_session_count()
            self.stat_sessions["val"].config(text=str(session_count))

            health_data = db.get_health_history(limit=100)
            latency_data = db.get_latency_history(limit=100)
            loss_data = db.get_packet_loss_history(limit=100)
            dns_data = db.get_dns_history(limit=100)

            # Avg health
            if health_data:
                avg_h = sum(d["score"] for d in health_data) / len(health_data)
                color = cfg.COLOR_SUCCESS if avg_h >= 75 else (cfg.COLOR_WARNING if avg_h >= 50 else cfg.COLOR_FAILURE)
                self.stat_avg_health["val"].config(text=f"{avg_h:.0f}", fg=color)

            # Avg latency
            valid_lats = [d["avg_ms"] for d in latency_data if d["avg_ms"] is not None and d["avg_ms"] >= 0]
            if valid_lats:
                avg_l = sum(valid_lats) / len(valid_lats)
                self.stat_avg_latency["val"].config(text=f"{avg_l:.0f} ms")

            # DNS success rate
            if dns_data:
                ok = sum(1 for d in dns_data if d["is_working"])
                rate = (ok / len(dns_data)) * 100
                self.stat_uptime["val"].config(text=f"{rate:.0f}%")

            # ── Render Charts ──────────────────────────────────────────
            self._render_health_chart(health_data)
            self._render_latency_chart(latency_data)
            self._render_loss_chart(loss_data)
            self._render_dns_chart(dns_data)

            # ── Session Table ──────────────────────────────────────────
            sessions = db.get_recent_sessions(limit=50)
            self._populate_table(sessions)

        except Exception:
            pass

    def _parse_ts(self, ts_str: str) -> datetime:
        """Parse timestamp string."""
        try:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now()

    def _render_health_chart(self, data):
        """Render health score trend line."""
        self.health_ax.clear()
        self._style_axis(self.health_ax)

        if not data:
            self.health_ax.text(
                0.5, 0.5, "No data yet — run diagnostics to begin",
                transform=self.health_ax.transAxes,
                ha="center", va="center",
                color=cfg.COLOR_TEXT_MUTED, fontsize=9,
            )
            self.health_fig.tight_layout(pad=1.0)
            self.health_canvas.draw_idle()
            return

        times = [self._parse_ts(d["timestamp"]) for d in data]
        scores = [d["score"] for d in data]

        self.health_ax.fill_between(times, scores, alpha=0.15, color="#22C55E")
        self.health_ax.plot(times, scores, color="#22C55E", linewidth=1.8, marker="o", markersize=3)
        self.health_ax.set_ylim(0, 105)
        self.health_ax.axhline(y=75, color=cfg.COLOR_WARNING, linestyle="--", alpha=0.4, linewidth=0.8)
        self.health_ax.axhline(y=50, color=cfg.COLOR_FAILURE, linestyle="--", alpha=0.4, linewidth=0.8)

        if len(times) > 6:
            self.health_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        else:
            self.health_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        self.health_fig.autofmt_xdate()
        self.health_fig.tight_layout(pad=1.0)
        self.health_canvas.draw_idle()

    def _render_latency_chart(self, data):
        """Render latency trend with min/max band."""
        self.latency_ax.clear()
        self._style_axis(self.latency_ax)

        valid = [d for d in data if d["avg_ms"] is not None and d["avg_ms"] >= 0]
        if not valid:
            self.latency_ax.text(
                0.5, 0.5, "No latency data",
                transform=self.latency_ax.transAxes,
                ha="center", va="center",
                color=cfg.COLOR_TEXT_MUTED, fontsize=9,
            )
            self.latency_fig.tight_layout(pad=1.0)
            self.latency_canvas.draw_idle()
            return

        times = [self._parse_ts(d["timestamp"]) for d in valid]
        avgs = [d["avg_ms"] for d in valid]
        mins = [d["min_ms"] for d in valid]
        maxs = [d["max_ms"] for d in valid]

        self.latency_ax.fill_between(times, mins, maxs, alpha=0.15, color=cfg.COLOR_ACCENT)
        self.latency_ax.plot(times, avgs, color=cfg.COLOR_ACCENT, linewidth=1.8, marker="o", markersize=3, label="Avg")
        self.latency_ax.plot(times, mins, color=cfg.COLOR_SUCCESS, linewidth=0.8, linestyle="--", alpha=0.6, label="Min")
        self.latency_ax.plot(times, maxs, color=cfg.COLOR_WARNING, linewidth=0.8, linestyle="--", alpha=0.6, label="Max")
        self.latency_ax.legend(fontsize=7, loc="upper right",
                               facecolor=cfg.COLOR_PANEL_DARK, edgecolor=cfg.COLOR_PANEL_ALT,
                               labelcolor=cfg.COLOR_TEXT_MUTED)

        if len(times) > 6:
            self.latency_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        else:
            self.latency_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        self.latency_fig.autofmt_xdate()
        self.latency_fig.tight_layout(pad=1.0)
        self.latency_canvas.draw_idle()

    def _render_loss_chart(self, data):
        """Render packet loss bar chart."""
        self.loss_ax.clear()
        self._style_axis(self.loss_ax)

        valid = [d for d in data if d["loss_pct"] is not None]
        if not valid:
            self.loss_ax.text(
                0.5, 0.5, "No packet loss data",
                transform=self.loss_ax.transAxes,
                ha="center", va="center",
                color=cfg.COLOR_TEXT_MUTED, fontsize=9,
            )
            self.loss_fig.tight_layout(pad=1.0)
            self.loss_canvas.draw_idle()
            return

        times = [self._parse_ts(d["timestamp"]) for d in valid]
        losses = [d["loss_pct"] for d in valid]
        colors = [cfg.COLOR_SUCCESS if l == 0 else (cfg.COLOR_WARNING if l <= 5 else cfg.COLOR_FAILURE) for l in losses]

        bar_width = 0.0003 if len(times) > 10 else 0.001
        self.loss_ax.bar(times, losses, width=bar_width, color=colors, alpha=0.85)
        self.loss_ax.set_ylim(0, max(max(losses) + 5, 10))

        if len(times) > 6:
            self.loss_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        else:
            self.loss_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        self.loss_fig.autofmt_xdate()
        self.loss_fig.tight_layout(pad=1.0)
        self.loss_canvas.draw_idle()

    def _render_dns_chart(self, data):
        """Render DNS status timeline (1=OK, 0=Failed)."""
        self.dns_ax.clear()
        self._style_axis(self.dns_ax)

        if not data:
            self.dns_ax.text(
                0.5, 0.5, "No DNS history",
                transform=self.dns_ax.transAxes,
                ha="center", va="center",
                color=cfg.COLOR_TEXT_MUTED, fontsize=9,
            )
            self.dns_fig.tight_layout(pad=1.0)
            self.dns_canvas.draw_idle()
            return

        times = [self._parse_ts(d["timestamp"]) for d in data]
        statuses = [d["is_working"] for d in data]
        colors = [cfg.COLOR_SUCCESS if s else cfg.COLOR_FAILURE for s in statuses]

        self.dns_ax.scatter(times, statuses, c=colors, s=30, zorder=3)
        self.dns_ax.step(times, statuses, where="post", color=cfg.COLOR_ACCENT, linewidth=1.0, alpha=0.5)
        self.dns_ax.set_ylim(-0.2, 1.3)
        self.dns_ax.set_yticks([0, 1])
        self.dns_ax.set_yticklabels(["Failed", "OK"], fontsize=7)

        if len(times) > 6:
            self.dns_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        else:
            self.dns_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        self.dns_fig.autofmt_xdate()
        self.dns_fig.tight_layout(pad=1.0)
        self.dns_canvas.draw_idle()

    def _populate_table(self, sessions):
        """Fill session history treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for s in sessions:
            ts = s.get("timestamp", "")
            health = s.get("health_score", "—")
            status = s.get("rca_status", "—")
            lat = s.get("avg_latency_ms", -1)
            lat_str = f"{lat:.0f}ms" if lat is not None and lat >= 0 else "N/A"
            loss = s.get("packet_loss_pct", -1)
            loss_str = f"{loss:.0f}%" if loss is not None and loss >= 0 else "N/A"
            dns = "✓" if s.get("dns_working") else "✗"
            adapter = s.get("adapter_name", "—")

            self.tree.insert("", "end", values=(ts, health, status, lat_str, loss_str, dns, adapter))

        self.lbl_table_count.config(text=f"{len(sessions)} sessions")

    def update_data(self, result: DiagnosticResult):
        """Refresh charts and table with latest data after a new scan."""
        self._load_history()
