"""
network_info_view.py — IntelliNet Network Information View
Presents detailed network configuration, Wi-Fi parameters, and interface traffic statistics.
"""

import tkinter as tk
from tkinter import ttk
import config as cfg
from models import DiagnosticResult


def _format_bytes(num_bytes: int) -> str:
    """Format bytes into readable KB, MB, or GB."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


class NetworkInfoView(tk.Frame):
    """
    Detailed Network Configuration Page:
      - Section 1: Adapter & TCP/IP Settings
      - Section 2: Wi-Fi Link & Radio Parameters
      - Section 3: Interface Traffic & Packet Counters
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=cfg.COLOR_BG, **kw)
        self.labels = {}
        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=cfg.COLOR_BG)
        container.pack(fill="both", expand=True, padx=24, pady=16)

        # 2 Columns layout: Left (Adapter & Traffic), Right (Wi-Fi Details)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        # ═══════════════════════════════════════════════════════════════
        # LEFT COLUMN
        # ═══════════════════════════════════════════════════════════════
        col_left = tk.Frame(container, bg=cfg.COLOR_BG)
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # ── Card 1: Adapter & IP Configuration ───────────────────────
        card_ip = self._create_section(col_left, "🔌  Network Adapter & IP Settings")
        self._add_row(card_ip, "Interface Name", "adapter_name", "Detecting...")
        self._add_row(card_ip, "Interface Type", "adapter_type", "—")
        self._add_row(card_ip, "Link Status", "adapter_status", "—")
        self._add_row(card_ip, "MAC Address", "mac_address", "—")
        self._add_row(card_ip, "Link Speed", "link_speed", "—")
        self._add_row(card_ip, "IPv4 Address", "ip_address", "—")
        self._add_row(card_ip, "Subnet Mask", "subnet_mask", "—")
        self._add_row(card_ip, "Default Gateway", "gateway_ip", "—")
        self._add_row(card_ip, "Gateway Reachability", "gateway_reach", "—")

        # ── Card 2: Traffic Counters (psutil) ────────────────────────
        card_traffic = self._create_section(col_left, "📊  Interface Traffic Counters")
        self._add_row(card_traffic, "Bytes Sent", "bytes_sent", "—")
        self._add_row(card_traffic, "Bytes Received", "bytes_recv", "—")
        self._add_row(card_traffic, "Packets Sent", "packets_sent", "—")
        self._add_row(card_traffic, "Packets Received", "packets_recv", "—")
        self._add_row(card_traffic, "Packet Errors (In / Out)", "errors", "—")
        self._add_row(card_traffic, "Packet Drops (In / Out)", "drops", "—")

        # ═══════════════════════════════════════════════════════════════
        # RIGHT COLUMN
        # ═══════════════════════════════════════════════════════════════
        col_right = tk.Frame(container, bg=cfg.COLOR_BG)
        col_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # ── Card 3: Wi-Fi & Wireless Parameters ──────────────────────
        card_wifi = self._create_section(col_right, "📶  Wi-Fi & Wireless Link Details")
        self._add_row(card_wifi, "Connection Type", "wifi_status", "—")
        self._add_row(card_wifi, "Network SSID", "wifi_ssid", "—")
        self._add_row(card_wifi, "Access Point BSSID", "wifi_bssid", "—")

        # Signal Strength with Visual Meter
        sig_row = tk.Frame(card_wifi, bg=cfg.COLOR_PANEL)
        sig_row.pack(fill="x", pady=4)
        tk.Label(
            sig_row,
            text="Signal Strength",
            font=("Segoe UI", 9),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_MUTED,
        ).pack(side="left")

        self.lbl_sig_pct = tk.Label(
            sig_row,
            text="—",
            font=("Segoe UI", 9, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
        )
        self.lbl_sig_pct.pack(side="right")

        self.sig_bar = ttk.Progressbar(
            card_wifi,
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.sig_bar.pack(fill="x", pady=(2, 8))

        self._add_row(card_wifi, "Radio Standard", "wifi_radio", "—")
        self._add_row(card_wifi, "Channel & Band", "wifi_channel", "—")
        self._add_row(card_wifi, "Receive Rate", "wifi_rx", "—")
        self._add_row(card_wifi, "Transmit Rate", "wifi_tx", "—")

        # ── Card 4: DNS Configuration ────────────────────────────────
        card_dns = self._create_section(col_right, "🌐  DNS Resolution Targets")
        self._add_row(card_dns, "Primary Test Domain", "dns_domain", cfg.DNS_TEST_DOMAIN)
        self._add_row(card_dns, "Secondary Test Domain", "dns_sec_domain", cfg.DNS_TEST_DOMAIN_SECONDARY)
        self._add_row(card_dns, "Primary DNS IP Target", "dns_target", cfg.PING_TARGET_PRIMARY)
        self._add_row(card_dns, "Secondary DNS IP Target", "dns_sec_target", cfg.PING_TARGET_SECONDARY)
        self._add_row(card_dns, "DNS Status", "dns_status", "—")

    def _create_section(self, parent: tk.Frame, title: str) -> tk.Frame:
        """Helper to create a panel card container with header."""
        card = tk.Frame(
            parent,
            bg=cfg.COLOR_PANEL,
            padx=16,
            pady=14,
            highlightthickness=1,
            highlightbackground=cfg.COLOR_PANEL_ALT,
        )
        card.pack(fill="x", pady=(0, 14))

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg=cfg.COLOR_PANEL,
            fg=cfg.COLOR_TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 6))

        tk.Frame(card, bg=cfg.COLOR_PANEL_ALT, height=1).pack(fill="x", pady=(0, 8))
        return card

    def _add_row(self, card: tk.Frame, label_text: str, key: str, default_val: str):
        """Helper to create a key-value row with registered label."""
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
        self.labels[key] = val_lbl

    def update_data(self, result: DiagnosticResult):
        """Populate all fields with live network information."""
        a = result.adapter
        ip = result.ip
        gw = result.gateway
        w = result.wifi
        dns = result.dns
        stats = getattr(result, "interface_stats", {})

        # Adapter & IP
        self.labels["adapter_name"].config(text=a.name)
        self.labels["adapter_type"].config(text=a.adapter_type or "Physical")
        self.labels["adapter_status"].config(
            text="Connected ✓" if a.is_up else "Disconnected ✗",
            fg=cfg.COLOR_SUCCESS if a.is_up else cfg.COLOR_FAILURE,
        )
        self.labels["mac_address"].config(text=a.mac_address or "Not Available")
        self.labels["link_speed"].config(text=f"{a.speed_mbps} Mbps" if a.speed_mbps > 0 else "Active")
        self.labels["ip_address"].config(text=ip.ipv4)
        self.labels["subnet_mask"].config(text=ip.subnet_mask or "255.255.255.0")
        self.labels["gateway_ip"].config(text=gw.ip)
        self.labels["gateway_reach"].config(
            text="Reachable ✓" if gw.is_reachable else "Unreachable ✗",
            fg=cfg.COLOR_SUCCESS if gw.is_reachable else cfg.COLOR_FAILURE,
        )

        # Traffic
        if stats:
            self.labels["bytes_sent"].config(text=_format_bytes(stats.get("bytes_sent", 0)))
            self.labels["bytes_recv"].config(text=_format_bytes(stats.get("bytes_recv", 0)))
            self.labels["packets_sent"].config(text=f"{stats.get('packets_sent', 0):,}")
            self.labels["packets_recv"].config(text=f"{stats.get('packets_recv', 0):,}")
            self.labels["errors"].config(text=f"{stats.get('errin', 0)} in / {stats.get('errout', 0)} out")
            self.labels["drops"].config(text=f"{stats.get('dropin', 0)} in / {stats.get('dropout', 0)} out")

        # Wi-Fi
        if w.is_wifi:
            self.labels["wifi_status"].config(text="Wi-Fi (802.11 Wireless)", fg=cfg.COLOR_SUCCESS)
            self.labels["wifi_ssid"].config(text=w.ssid if w.ssid else "Connected")
            self.labels["wifi_bssid"].config(text=w.bssid if w.bssid else "N/A")

            sig = max(0, w.signal_pct)
            self.lbl_sig_pct.config(
                text=f"{sig}%",
                fg=cfg.COLOR_SUCCESS if sig >= 70 else (cfg.COLOR_WARNING if sig >= 40 else cfg.COLOR_FAILURE),
            )
            self.sig_bar["value"] = sig

            self.labels["wifi_radio"].config(text=w.radio_type if w.radio_type else "802.11 Standard")
            self.labels["wifi_channel"].config(text=f"Channel {w.channel}" if w.channel else "Auto")
            self.labels["wifi_rx"].config(text=f"{w.receive_rate_mbps} Mbps" if w.receive_rate_mbps > 0 else "N/A")
            self.labels["wifi_tx"].config(text=f"{w.transmit_rate_mbps} Mbps" if w.transmit_rate_mbps > 0 else "N/A")
        else:
            self.labels["wifi_status"].config(text="Wired / Ethernet Connection", fg=cfg.COLOR_TEXT_PRIMARY)
            self.labels["wifi_ssid"].config(text="N/A (Wired)")
            self.labels["wifi_bssid"].config(text="N/A (Wired)")
            self.lbl_sig_pct.config(text="100% (Wired)", fg=cfg.COLOR_SUCCESS)
            self.sig_bar["value"] = 100
            self.labels["wifi_radio"].config(text="IEEE 802.3 Ethernet")
            self.labels["wifi_channel"].config(text="N/A (Cable Link)")
            self.labels["wifi_rx"].config(text=f"{a.speed_mbps} Mbps" if a.speed_mbps > 0 else "1000 Mbps")
            self.labels["wifi_tx"].config(text=f"{a.speed_mbps} Mbps" if a.speed_mbps > 0 else "1000 Mbps")

        # DNS
        self.labels["dns_status"].config(
            text="Operational ✓" if dns.is_working else "Failed ✗",
            fg=cfg.COLOR_SUCCESS if dns.is_working else cfg.COLOR_FAILURE,
        )
