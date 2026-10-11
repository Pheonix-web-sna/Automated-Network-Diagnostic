"""
performance_view.py — IntelliNet Performance View
Visual latency meter, jitter analysis, packet loss breakdown, and network quality assessment.
"""

import tkinter as tk
from tkinter import ttk
import config as cfg
from models import DiagnosticResult


class LatencyMeterCanvas(tk.Canvas):
    """
    Horizontal colored segmented scale with an active marker indicating
    where the current latency falls across quality tiers.
    """
    WIDTH = 560
    HEIGHT = 44

    TIERS = [
        (0, 30, "Excellent", "#22C55E"),
        (30, 60, "Good", "#10B981"),
        (60, 100, "Fair", "#F59E0B"),
        (100, 200, "Poor", "#F97316"),
        (200, 300, "Critical", "#EF4444"),
    ]

    def __init__(self, parent, bg_color: str, **kw):
        super().__init__(
            parent,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=bg_color,
            highlightthickness=0,
            **kw
        )
        self._draw(-1)

    def _draw(self, latency_ms: float):
        self.delete("all")
        y_top = 10
        y_bot = 24
        total_w = self.WIDTH - 20
        seg_w = total_w / len(self.TIERS)

        # Draw segmented colored bar
        for i, (min_ms, max_ms, label, col) in enumerate(self.TIERS):
            x1 = 10 + i * seg_w
            x2 = x1 + seg_w - 2
            self.create_rectangle(x1, y_top, x2, y_bot, fill=col, outline="")

            # Tier label below
            self.create_text(
                (x1 + x2) / 2, y_bot + 10,
                text=f"{label} (≤{max_ms}ms)" if i < 4 else ">200ms",
                font=("Segoe UI", 7),
                fill=cfg.COLOR_TEXT_MUTED,
            )

        # Draw pointer marker if latency is valid
        if latency_ms >= 0:
            # Map latency 0–300ms to X position 10–(10+total_w)
            clamped = min(max(latency_ms, 0), 300)
            marker_x = 10 + (clamped / 300.0) * total_w

            # Top pointer triangle
            self.create_polygon(
                marker_x - 5, y_top - 6,
                marker_x + 5, y_top - 6,
                marker_x, y_top + 1,
                fill="#FFFFFF",
                outline="",
            )

            # Center text for current latency
            self.create_text(
                marker_x, y_top - 10,
                text=f"{latency_ms:.0f}ms",
                font=("Segoe UI", 8, "bold"),
                fill="#FFFFFF",
            )

    def update_latency(self, latency_ms: float):
        self._draw(latency_ms)


class PerformanceView(tk.Frame):
    """
    Dedicated Performance Analysis Page:
      - 4 Metric Highlight Cards (Avg Latency, Jitter, Packet Loss, RTT Spread)
      - Visual Latency Tier Scale
      - Packet Transmission & Loss Breakdown
      - Application Usability Assessment
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # ═══════════════════════════════════════════════════════════════
        # TOP ROW: 4 METRIC HIGHLIGHT CARDS
        # ═══════════════════════════════════════════════════════════════
        cards_row = tk.Frame(container, bg=cfg.COLOR_BG)
        cards_row.pack(fill="x", pady=(0, 16))
        for i in range(4):
            cards_row.columnconfigure(i, weight=1)

        # Card 1: Average Latency
        self.c_lat = self._metric_card(cards_row, 0, "AVERAGE LATENCY", "— ms", "Awaiting scan", cfg.COLOR_ACCENT)
        # Card 2: Jitter
        self.c_jit = self._metric_card(cards_row, 1, "LATENCY JITTER", "— ms", "RTT variation", cfg.COLOR_PURPLE)
        # Card 3: Packet Loss
        self.c_los = self._metric_card(cards_row, 2, "PACKET LOSS", "— %", "0 lost packets", cfg.COLOR_SUCCESS)
        # Card 4: RTT Spread
        self.c_rng = self._metric_card(cards_row, 3, "RTT RANGE (MIN/MAX)", "— / —", "Min / Max latency", cfg.COLOR_TEAL)

        # ═══════════════════════════════════════════════════════════════
        # MIDDLE SECTION: VISUAL LATENCY METER & PACKET DELIVERY
        # ═══════════════════════════════════════════════════════════════
        mid_row = tk.Frame(container, bg=cfg.COLOR_BG)
        mid_row.pack(fill="x", pady=(0, 16))
        mid_row.columnconfigure(0, weight=6)
        mid_row.columnconfigure(1, weight=4)

        # ── Left: Visual Latency Scale ──
        meter_card = tk.Frame(
            mid_row,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        meter_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(
            meter_card,
            text="LATENCY QUALITY TIER SCALE",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        self.meter = LatencyMeterCanvas(meter_card, bg_color=cfg.COLOR_PANEL)
        self.meter.pack(pady=(16, 10), fill="x")

        self.lbl_target_info = tk.Label(
            meter_card,
            text=f"Ping Target: {cfg.PING_TARGET_PRIMARY} (Google Public DNS) | Pings: {cfg.PING_COUNT} packets",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.lbl_target_info.pack(fill="x")

        # ── Right: Packet Delivery Breakdown ──
        packet_card = tk.Frame(
            mid_row,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        packet_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(
            packet_card,
            text="PACKET TRANSMISSION BREAKDOWN",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 10))

        self.lbl_pkt_summary = tk.Label(
            packet_card,
            text="Packet measurement pending",
            font=("Segoe UI", 11, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_SUCCESS,
            anchor="w",
        )
        self.lbl_pkt_summary.pack(fill="x", pady=(0, 6))

        self.pkt_progress = ttk.Progressbar(
            packet_card,
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.pkt_progress.pack(fill="x", pady=(0, 10))
        self.pkt_progress["value"] = 0

        self.lbl_pkt_detail = tk.Label(
            packet_card,
            text="No ping sequence completed",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.lbl_pkt_detail.pack(fill="x")

        # ═══════════════════════════════════════════════════════════════
        # BOTTOM SECTION: APPLICATION USABILITY ASSESSMENT
        # ═══════════════════════════════════════════════════════════════
        eval_card = tk.Frame(
            container,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        eval_card.pack(fill="both", expand=True)

        tk.Label(
            eval_card,
            text="NETWORK QUALITY & USABILITY ASSESSMENT",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 10))

        eval_grid = tk.Frame(eval_card, bg=cfg.COLOR_PANEL)
        eval_grid.pack(fill="both", expand=True)
        for i in range(4):
            eval_grid.columnconfigure(i, weight=1)

        self.app_browsing  = self._app_tile(eval_grid, 0, "🌐  Web Browsing", "Pending scan")
        self.app_calls     = self._app_tile(eval_grid, 1, "📞  Voice / Video Calls", "Pending scan")
        self.app_gaming    = self._app_tile(eval_grid, 2, "🎮  Online Gaming", "Pending scan")
        self.app_downloads = self._app_tile(eval_grid, 3, "📥  Streaming & Media", "Pending scan")

    def _metric_card(self, parent: tk.Frame, col: int, title: str, default_val: str, subtitle: str, color: str) -> dict:
        """Helper to create a high-impact metric highlight card."""
        card = tk.Frame(
            parent,
            bg=cfg.COLOR_PANEL,
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        card.grid(row=0, column=col, sticky="nsew", padx=4)

        tk.Label(
            card, text=title, font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED, anchor="w"
        ).pack(fill="x")

        val_lbl = tk.Label(
            card, text=default_val, font=("Segoe UI", 18, "bold"),
            bg=cfg.COLOR_PANEL, fg=color, anchor="w"
        )
        val_lbl.pack(fill="x", pady=(4, 2))

        sub_lbl = tk.Label(
            card, text=subtitle, font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL, fg=cfg.COLOR_TEXT_MUTED, anchor="w"
        )
        sub_lbl.pack(fill="x")

        return {"card": card, "val": val_lbl, "sub": sub_lbl}

    def _app_tile(self, parent: tk.Frame, col: int, app_name: str, default_status: str) -> dict:
        """Helper to create an application usability assessment card."""
        tile = tk.Frame(
            parent,
            bg=cfg.COLOR_PANEL_DARK,
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL,
        )
        tile.grid(row=0, column=col, sticky="nsew", padx=4)

        tk.Label(
            tile, text=app_name, font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_PRIMARY, anchor="w"
        ).pack(fill="x")

        status_lbl = tk.Label(
            tile, text=default_status, font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL_DARK, fg=cfg.COLOR_TEXT_MUTED, anchor="w"
        )
        status_lbl.pack(fill="x", pady=(4, 0))

        return {"status": status_lbl, "tile": tile}

    def update_data(self, result: DiagnosticResult):
        """Update metrics and assessments using measured PerformanceMetrics."""
        p = result.performance
        if p.is_valid:
            lat = p.avg_latency_ms
            lat_col = (
                cfg.COLOR_SUCCESS if lat <= cfg.LATENCY_GOOD_MS else
                (cfg.COLOR_WARNING if lat <= cfg.LATENCY_FAIR_MS else cfg.COLOR_FAILURE)
            )
            self.c_lat["val"].config(text=f"{lat:.0f} ms", fg=lat_col)
            self.c_lat["sub"].config(text=f"Rating: {p.latency_rating}")
            self.c_jit["val"].config(text=f"{p.jitter_ms:.0f} ms")
            self.c_jit["sub"].config(
                text="Stable delay" if p.jitter_ms <= cfg.JITTER_STABLE_MS else "Variable network delay",
                fg=cfg.COLOR_SUCCESS if p.jitter_ms <= cfg.JITTER_STABLE_MS else cfg.COLOR_WARNING,
            )
            self.c_rng["val"].config(text=f"{p.min_latency_ms:.0f}ms / {p.max_latency_ms:.0f}ms")
            self.c_rng["sub"].config(text=f"Difference: {p.jitter_ms:.0f}ms")
            self.meter.update_latency(lat)
            self.lbl_target_info.config(
                text=f"Ping target: {p.target_host} | {p.ping_count} probes | Average {lat:.1f}ms",
            )
        else:
            reason = p.error or "Latency measurement unavailable"
            self.c_lat["val"].config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
            self.c_lat["sub"].config(text=reason)
            self.c_jit["val"].config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
            self.c_jit["sub"].config(text="Not measured", fg=cfg.COLOR_TEXT_MUTED)
            self.c_rng["val"].config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
            self.c_rng["sub"].config(text="Not measured", fg=cfg.COLOR_TEXT_MUTED)
            self.meter.update_latency(-1)
            self.lbl_target_info.config(
                text=f"Ping target: {p.target_host or 'Not available'} | {reason}",
            )

        if p.has_packet_measurement:
            loss = p.packet_loss_pct
            received = round(p.ping_count * (1 - loss / 100))
            lost = p.ping_count - received
            delivery_pct = 100.0 - loss
            loss_col = cfg.COLOR_SUCCESS if loss <= cfg.LOSS_GOOD_PCT else (
                cfg.COLOR_WARNING if loss <= cfg.LOSS_FAIR_PCT else cfg.COLOR_FAILURE
            )
            self.c_los["val"].config(text=f"{loss:.0f}%", fg=loss_col)
            self.c_los["sub"].config(text=f"{lost} lost of {p.ping_count} probes")
            self.lbl_pkt_summary.config(
                text=f"{received} / {p.ping_count} probes received ({delivery_pct:.0f}% delivery)",
                fg=loss_col,
            )
            self.pkt_progress["value"] = delivery_pct
            self.lbl_pkt_detail.config(
                text=f"Sent: {p.ping_count} | Received: {received} | Lost: {lost} ({loss:.0f}% loss)"
            )
        else:
            self.c_los["val"].config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
            self.c_los["sub"].config(text="No packet measurement", fg=cfg.COLOR_TEXT_MUTED)
            self.lbl_pkt_summary.config(text="Packet loss unavailable", fg=cfg.COLOR_TEXT_MUTED)
            self.pkt_progress["value"] = 0
            self.lbl_pkt_detail.config(text=p.error or "No ping sequence was completed.")

        if not result.internet.is_connected or not p.is_valid or not p.has_packet_measurement:
            if not result.internet.is_connected:
                text = "Internet unavailable; application quality cannot be estimated."
            elif not p.is_valid:
                text = "Insufficient latency data to estimate application quality."
            else:
                text = "Packet-loss measurement unavailable; application quality cannot be estimated."
            for tile in (
                self.app_browsing, self.app_calls, self.app_gaming, self.app_downloads
            ):
                tile["status"].config(text=text, fg=cfg.COLOR_TEXT_MUTED)
            return

        lat = p.avg_latency_ms
        loss = p.packet_loss_pct if p.has_packet_measurement else 0
        if lat <= cfg.LATENCY_EXCELLENT_MS and loss <= cfg.LOSS_EXCELLENT_PCT:
            labels = (
                "Excellent — Instant page loads", "Crystal Clear — Low latency",
                "Optimal — Competitive grade", "Maximum throughput",
            )
            color = cfg.COLOR_SUCCESS
        elif lat <= cfg.LATENCY_GOOD_MS and loss <= cfg.LOSS_GOOD_PCT:
            labels = (
                "Good — Responsive browsing", "Good — Minor delay",
                "Playable — Moderate latency", "Stable streaming",
            )
            color = cfg.COLOR_SUCCESS
        elif lat <= cfg.LATENCY_POOR_MS and loss <= cfg.LOSS_POOR_PCT:
            labels = (
                "Fair — Noticeable lag", "Degraded — Possible audio drops",
                "Poor — High input delay", "Occasional buffering",
            )
            color = cfg.COLOR_WARNING
        else:
            labels = (
                "Critical — Severe slowdowns", "Unusable — Calls may disconnect",
                "Unplayable — High lag or loss", "Frequent timeouts",
            )
            color = cfg.COLOR_FAILURE
        for tile, label in zip(
            (self.app_browsing, self.app_calls, self.app_gaming, self.app_downloads),
            labels,
        ):
            tile["status"].config(text=label, fg=color)
