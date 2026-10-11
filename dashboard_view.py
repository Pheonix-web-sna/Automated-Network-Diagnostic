"""
dashboard_view.py — IntelliNet Dashboard View
Overview screen featuring Health Score gauge, RCA banner, and 4 status cards.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import config as cfg
from models import DiagnosticResult


class HealthGaugeCanvas(tk.Canvas):
    """
    Circular arc gauge displaying Health Score 0–100.
    Drawn cleanly with Tkinter Canvas primitives.
    """
    SIZE = 120
    THICKNESS = 11
    START_ANGLE = 220
    SWEEP_TOTAL = -260

    def __init__(self, parent, bg_color: str, **kw):
        super().__init__(
            parent,
            width=self.SIZE,
            height=self.SIZE,
            bg=bg_color,
            highlightthickness=0,
            **kw
        )
        self._bg_color = bg_color
        self._draw(0, cfg.COLOR_TEXT_MUTED)

    def _draw(self, score: int, color: str):
        self.delete("all")
        pad = self.THICKNESS + 6
        x0, y0 = pad, pad
        x1, y1 = self.SIZE - pad, self.SIZE - pad

        # Background track
        self.create_arc(
            x0, y0, x1, y1,
            start=self.START_ANGLE,
            extent=self.SWEEP_TOTAL,
            style="arc",
            outline=cfg.COLOR_PANEL_ALT,
            width=self.THICKNESS,
        )

        # Active score arc
        if score > 0:
            sweep = self.SWEEP_TOTAL * (score / 100.0)
            self.create_arc(
                x0, y0, x1, y1,
                start=self.START_ANGLE,
                extent=sweep,
                style="arc",
                outline=color,
                width=self.THICKNESS,
            )

        # Center score text
        cx = self.SIZE // 2
        cy = self.SIZE // 2 - 4
        self.create_text(
            cx, cy,
            text=str(score),
            font=("Segoe UI", 22, "bold"),
            fill=color,
        )
        self.create_text(
            cx, cy + 22,
            text="/100",
            font=("Segoe UI", 8),
            fill=cfg.COLOR_TEXT_MUTED,
        )

    def update_score(self, score: int, color: str):
        self._draw(score, color)


class DashboardView(tk.Frame):
    """
    Main overview dashboard:
      - Left Hero Card: Network Health Score gauge + Layer breakdown
      - Right Hero Card: RCA Summary, Confidence score, and Status
      - 4 Network Status Cards: Interface, IP/Gateway, DNS/Internet, Performance
    """

    def __init__(self, parent, on_view_recommendations: Optional[Callable[[], None]] = None, **kw):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self.on_view_recommendations = on_view_recommendations
        self._build_ui()

    def _build_ui(self):
        # Scrollable container for smaller screens
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = tk.Frame(self, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # ═══════════════════════════════════════════════════════════════
        # TOP ROW: HERO CARDS (Health Score & RCA Status)
        # ═══════════════════════════════════════════════════════════════
        hero_row = tk.Frame(container, bg=cfg.COLOR_BG)
        hero_row.pack(fill="x", pady=(0, 16))
        hero_row.columnconfigure(0, weight=4)
        hero_row.columnconfigure(1, weight=6)

        # ── Card 1: Network Health Score ──────────────────────────────
        self.health_card = tk.Frame(
            hero_row,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        self.health_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Health header
        h_title_row = tk.Frame(self.health_card, bg=cfg.COLOR_PANEL)
        h_title_row.pack(fill="x")
        tk.Label(
            h_title_row,
            text="NETWORK HEALTH SCORE",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.health_badge = tk.Label(
            h_title_row,
            text="PENDING",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_ALT,
            fg=cfg.COLOR_TEXT_MUTED,
            padx=6,
            pady=1,
        )
        self.health_badge.pack(side="right")

        # Gauge + Breakdown layout
        h_body = tk.Frame(self.health_card, bg=cfg.COLOR_PANEL)
        h_body.pack(fill="both", expand=True, pady=(12, 0))

        # Left: Gauge
        gauge_box = tk.Frame(h_body, bg=cfg.COLOR_PANEL)
        gauge_box.pack(side="left", padx=(0, 16))

        self.gauge = HealthGaugeCanvas(gauge_box, bg_color=cfg.COLOR_PANEL)
        self.gauge.pack()

        self.gauge_rating = tk.Label(
            gauge_box,
            text="Not Scanned",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        )
        self.gauge_rating.pack(pady=(4, 0))

        # Right: Layer Component Bars
        self.breakdown_frame = tk.Frame(h_body, bg=cfg.COLOR_PANEL)
        self.breakdown_frame.pack(side="left", fill="both", expand=True)

        self.comp_labels = {}
        components = [
            ("adapter", "Adapter State", cfg.HEALTH_WEIGHTS["adapter"]),
            ("ip", "IP Configuration", cfg.HEALTH_WEIGHTS["ip"]),
            ("gateway", "Gateway Reachability", cfg.HEALTH_WEIGHTS["gateway"]),
            ("dns", "DNS Resolution", cfg.HEALTH_WEIGHTS["dns"]),
            ("internet", "Internet Access", cfg.HEALTH_WEIGHTS["internet"]),
            ("performance", "Latency & Loss", cfg.HEALTH_WEIGHTS["latency"] + cfg.HEALTH_WEIGHTS["packet_loss"]),
        ]

        for cid, cname, cweight in components:
            row = tk.Frame(self.breakdown_frame, bg=cfg.COLOR_PANEL)
            row.pack(fill="x", pady=2)

            name_lbl = tk.Label(
                row,
                text=cname,
                font=("Segoe UI", 8),
                bg=cfg.COLOR_PANEL,
                fg=cfg.COLOR_TEXT_PRIMARY,
                anchor="w",
            )
            name_lbl.pack(side="left")

            val_lbl = tk.Label(
                row,
                text=f"— / {cweight} pts",
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL,
                fg=cfg.COLOR_TEXT_MUTED,
                anchor="e",
            )
            val_lbl.pack(side="right")
            self.comp_labels[cid] = val_lbl

        # ── Card 2: Root Cause Analysis & Status ─────────────────────
        self.rca_card = tk.Frame(
            hero_row,
            bg=cfg.COLOR_PANEL,
            padx=18,
            pady=16,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        self.rca_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        r_title_row = tk.Frame(self.rca_card, bg=cfg.COLOR_PANEL)
        r_title_row.pack(fill="x")
        tk.Label(
            r_title_row,
            text="ROOT CAUSE ANALYSIS & DIAGNOSIS",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.conf_badge = tk.Label(
            r_title_row,
            text="CONFIDENCE: —",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL_ALT,
            fg=cfg.COLOR_TEXT_MUTED,
            padx=6,
            pady=1,
        )
        self.conf_badge.pack(side="right")

        # Overall Status Badge
        self.status_banner = tk.Label(
            self.rca_card,
            text="SYSTEM READY — RUN SCAN TO DIAGNOSE",
            font=("Segoe UI", 11, "bold"),
            bg="#131C2E",
            fg=cfg.COLOR_ACCENT,
            padx=12,
            pady=8,
            anchor="w",
        )
        self.status_banner.pack(fill="x", pady=(10, 8))

        # Primary Diagnosis text
        tk.Label(
            self.rca_card,
            text="Primary Diagnosis:",
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

        self.primary_cause_lbl = tk.Label(
            self.rca_card,
            text="Click 'Run Diagnostics' above to perform a real-time network evaluation.",
            font=("Segoe UI", 9),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
            wraplength=480,
            justify="left",
            anchor="w",
        )
        self.primary_cause_lbl.pack(fill="x", pady=(2, 8))

        # Bottom row of RCA card: Recommendation CTA
        rca_footer = tk.Frame(self.rca_card, bg=cfg.COLOR_PANEL)
        rca_footer.pack(fill="x", side="bottom")

        self.secondary_cause_lbl = tk.Label(
            rca_footer,
            text="",
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_WARNING,
            anchor="w",
        )
        self.secondary_cause_lbl.pack(side="left", fill="x", expand=True)

        if self.on_view_recommendations:
            self.btn_rec_link = tk.Button(
                rca_footer,
                text="View Recommendations →",
                font=("Segoe UI", 8, "bold"),
                bg=cfg.COLOR_PANEL_ALT,
                fg=cfg.COLOR_ACCENT,
                activebackground=cfg.COLOR_ACCENT,
                activeforeground="#FFFFFF",
                relief="flat",
                cursor="hand2",
                command=self.on_view_recommendations,
                padx=10,
                pady=4,
            )
            self.btn_rec_link.pack(side="right")

        # ═══════════════════════════════════════════════════════════════
        # BOTTOM ROW: 4 NETWORK STATUS CARDS
        # ═══════════════════════════════════════════════════════════════
        grid_row = tk.Frame(container, bg=cfg.COLOR_BG)
        grid_row.pack(fill="both", expand=True)
        for i in range(4):
            grid_row.columnconfigure(i, weight=1)

        # ── Card 1: Network Interface ──
        self.card_adapter = self._create_card(grid_row, 0, "🔌  Network Adapter")
        self.lbl_ad_name  = self._add_card_row(self.card_adapter, "Adapter", "Detecting...")
        self.lbl_ad_type  = self._add_card_row(self.card_adapter, "Type", "—")
        self.lbl_ad_speed = self._add_card_row(self.card_adapter, "Speed", "—")
        self.lbl_ad_mac   = self._add_card_row(self.card_adapter, "MAC", "—")

        # ── Card 2: IP & Gateway ──
        self.card_ip = self._create_card(grid_row, 1, "🌐  IP & Gateway")
        self.lbl_ip_addr = self._add_card_row(self.card_ip, "IPv4", "—")
        self.lbl_ip_mask = self._add_card_row(self.card_ip, "Subnet", "—")
        self.lbl_gw_ip   = self._add_card_row(self.card_ip, "Gateway", "—")
        self.lbl_gw_ping = self._add_card_row(self.card_ip, "Ping GW", "—")

        # ── Card 3: DNS & Internet ──
        self.card_dns = self._create_card(grid_row, 2, "🌍  DNS & Internet")
        self.lbl_dns_test = self._add_card_row(self.card_dns, "DNS Test", cfg.DNS_TEST_DOMAIN)
        self.lbl_dns_res  = self._add_card_row(self.card_dns, "Resolution", "—")
        self.lbl_inet_ip  = self._add_card_row(self.card_dns, "Internet IP", cfg.PING_TARGET_PRIMARY)
        self.lbl_inet_con = self._add_card_row(self.card_dns, "Connectivity", "—")

        # ── Card 4: Performance & Wi-Fi ──
        self.card_perf = self._create_card(grid_row, 3, "⚡  Performance & Wi-Fi")
        self.lbl_perf_lat  = self._add_card_row(self.card_perf, "Avg Latency", "—")
        self.lbl_perf_loss = self._add_card_row(self.card_perf, "Packet Loss", "—")
        self.lbl_wifi_ssid = self._add_card_row(self.card_perf, "SSID", "—")
        self.lbl_wifi_sig  = self._add_card_row(self.card_perf, "Signal", "—")

    def _create_card(self, parent: tk.Frame, col: int, title: str) -> tk.Frame:
        """Helper to create a modern padded card with header and border."""
        card = tk.Frame(
            parent,
            bg=cfg.COLOR_PANEL,
            padx=14,
            pady=14,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        card.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)

        header = tk.Frame(card, bg=cfg.COLOR_PANEL)
        header.pack(fill="x", pady=(0, 10))

        tk.Label(
            header,
            text=title,
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
        ).pack(side="left")

        # Subtle card line
        tk.Frame(card, bg=cfg.COLOR_PANEL_ALT, height=1).pack(fill="x", pady=(0, 8))

        return card

    def _add_card_row(self, card: tk.Frame, label_text: str, default_val: str) -> tk.Label:
        """Helper to add key-value row to a card."""
        row = tk.Frame(card, bg=cfg.COLOR_PANEL)
        row.pack(fill="x", pady=3)

        tk.Label(
            row,
            text=label_text,
            font=("Segoe UI", 8),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
            anchor="w",
        ).pack(side="left")

        val_lbl = tk.Label(
            row,
            text=default_val,
            font=("Segoe UI", 8, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
            anchor="e",
        )
        val_lbl.pack(side="right")
        return val_lbl

    def update_data(self, result: DiagnosticResult):
        """Update all widgets on the dashboard with a fresh DiagnosticResult."""
        hlth = result.health
        rca  = result.rca
        perf = result.performance

        # ── Health Score ──────────────────────────────────────────────
        self.gauge.update_score(hlth.score, hlth.color)
        self.gauge_rating.config(text=hlth.label, fg=hlth.color)

        self.health_badge.config(
            text=f"{hlth.score}/100",
            bg=hlth.color,
            fg="#FFFFFF" if hlth.score < 55 or hlth.score >= 80 else "#0F172A",
        )

        # Update breakdown labels
        c = hlth.components
        if "adapter" in c:
            self.comp_labels["adapter"].config(
                text=f"{c['adapter']} / {cfg.HEALTH_WEIGHTS['adapter']} pts",
                fg=cfg.COLOR_SUCCESS if c["adapter"] == cfg.HEALTH_WEIGHTS["adapter"] else cfg.COLOR_FAILURE,
            )
        if "ip" in c:
            self.comp_labels["ip"].config(
                text=f"{c['ip']} / {cfg.HEALTH_WEIGHTS['ip']} pts",
                fg=cfg.COLOR_SUCCESS if c["ip"] == cfg.HEALTH_WEIGHTS["ip"] else cfg.COLOR_FAILURE,
            )
        if "gateway" in c:
            self.comp_labels["gateway"].config(
                text=f"{c['gateway']} / {cfg.HEALTH_WEIGHTS['gateway']} pts",
                fg=cfg.COLOR_SUCCESS if c["gateway"] == cfg.HEALTH_WEIGHTS["gateway"] else cfg.COLOR_FAILURE,
            )
        if "dns" in c:
            self.comp_labels["dns"].config(
                text=f"{c['dns']} / {cfg.HEALTH_WEIGHTS['dns']} pts",
                fg=cfg.COLOR_SUCCESS if c["dns"] == cfg.HEALTH_WEIGHTS["dns"] else cfg.COLOR_FAILURE,
            )
        if "internet" in c:
            self.comp_labels["internet"].config(
                text=f"{c['internet']} / {cfg.HEALTH_WEIGHTS['internet']} pts",
                fg=cfg.COLOR_SUCCESS if c["internet"] == cfg.HEALTH_WEIGHTS["internet"] else cfg.COLOR_FAILURE,
            )
        lat_pts = c.get("latency", 0)
        loss_pts = c.get("packet_loss", 0)
        tot_perf = lat_pts + loss_pts
        self.comp_labels["performance"].config(
            text=f"{tot_perf} / {cfg.HEALTH_WEIGHTS['latency'] + cfg.HEALTH_WEIGHTS['packet_loss']} pts",
            fg=cfg.COLOR_SUCCESS if tot_perf >= 8 else (cfg.COLOR_WARNING if tot_perf >= 4 else cfg.COLOR_FAILURE),
        )

        # ── RCA & Status Card ─────────────────────────────────────────
        status_colors = {
            "CRITICAL":    cfg.COLOR_FAILURE,
            "WARNING":     cfg.COLOR_WARNING,
            "PERFORMANCE": cfg.COLOR_WARNING,
            "NORMAL":      cfg.COLOR_SUCCESS,
        }
        color = status_colors.get(rca.severity, cfg.COLOR_ACCENT)
        self.status_banner.config(text=f"●  {rca.overall_status}", fg=color)
        self.primary_cause_lbl.config(text=rca.primary_cause)

        self.conf_badge.config(
            text=f"CONFIDENCE: {rca.confidence}%",
            fg=cfg.COLOR_PURPLE,
            bg=cfg.COLOR_PANEL_ALT,
        )

        if rca.secondary_causes:
            self.secondary_cause_lbl.config(text=f"Note: {rca.secondary_causes[0]}")
        else:
            self.secondary_cause_lbl.config(text="")

        # ── Card 1: Network Adapter ───────────────────────────────────
        a = result.adapter
        self.lbl_ad_name.config(text=a.name[:18])
        self.lbl_ad_type.config(text=a.adapter_type or "Physical")
        self.lbl_ad_speed.config(text=f"{a.speed_mbps} Mbps" if a.speed_mbps > 0 else "Active")
        self.lbl_ad_mac.config(text=a.mac_address or "N/A")

        # ── Card 2: IP & Gateway ──────────────────────────────────────
        self.lbl_ip_addr.config(text=result.ip.ipv4)
        self.lbl_ip_mask.config(text=result.ip.subnet_mask or "Not available")
        self.lbl_gw_ip.config(text=result.gateway.ip)
        self.lbl_gw_ping.config(
            text="Reachable ✓" if result.gateway.is_reachable else "Unreachable ✗",
            fg=cfg.COLOR_SUCCESS if result.gateway.is_reachable else cfg.COLOR_FAILURE,
        )

        # ── Card 3: DNS & Internet ────────────────────────────────────
        self.lbl_dns_test.config(text=result.dns.domain_tested)
        self.lbl_dns_res.config(
            text="Working ✓" if result.dns.is_working else "Failed ✗",
            fg=cfg.COLOR_SUCCESS if result.dns.is_working else cfg.COLOR_FAILURE,
        )
        self.lbl_inet_ip.config(text=result.internet.target_ip)
        self.lbl_inet_con.config(
            text="Connected ✓" if result.internet.is_connected else "Unreachable ✗",
            fg=cfg.COLOR_SUCCESS if result.internet.is_connected else cfg.COLOR_FAILURE,
        )

        # ── Card 4: Performance & Wi-Fi ───────────────────────────────
        if perf.is_valid:
            lat_color = (
                cfg.COLOR_SUCCESS if perf.avg_latency_ms <= cfg.LATENCY_GOOD_MS else
                (cfg.COLOR_WARNING if perf.avg_latency_ms <= cfg.LATENCY_FAIR_MS else cfg.COLOR_FAILURE)
            )
            self.lbl_perf_lat.config(
                text=f"{perf.avg_latency_ms:.0f} ms ({perf.latency_rating})",
                fg=lat_color,
            )
            loss_color = cfg.COLOR_SUCCESS if perf.packet_loss_pct <= cfg.LOSS_GOOD_PCT else cfg.COLOR_FAILURE
            self.lbl_perf_loss.config(
                text=f"{perf.packet_loss_pct:.0f}%",
                fg=loss_color,
            )
        else:
            self.lbl_perf_lat.config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
            if perf.has_packet_measurement:
                loss_color = cfg.COLOR_SUCCESS if perf.packet_loss_pct <= cfg.LOSS_GOOD_PCT else cfg.COLOR_FAILURE
                self.lbl_perf_loss.config(text=f"{perf.packet_loss_pct:.0f}%", fg=loss_color)
            else:
                self.lbl_perf_loss.config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)

        w = result.wifi
        if w.is_wifi:
            self.lbl_wifi_ssid.config(text=w.ssid[:14] if w.ssid else "Connected")
            if w.signal_pct >= 0:
                sig_color = cfg.COLOR_SUCCESS if w.signal_pct >= 70 else (cfg.COLOR_WARNING if w.signal_pct >= 40 else cfg.COLOR_FAILURE)
                self.lbl_wifi_sig.config(text=f"{w.signal_pct}%", fg=sig_color)
            else:
                self.lbl_wifi_sig.config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
        elif a.is_up and a.adapter_type == "Ethernet":
            self.lbl_wifi_ssid.config(text="Wired Ethernet")
            self.lbl_wifi_sig.config(text="N/A (wired)", fg=cfg.COLOR_TEXT_MUTED)
        elif a.is_up:
            self.lbl_wifi_ssid.config(text="Not available")
            self.lbl_wifi_sig.config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
        else:
            self.lbl_wifi_ssid.config(text="Not connected")
            self.lbl_wifi_sig.config(text="N/A", fg=cfg.COLOR_TEXT_MUTED)
