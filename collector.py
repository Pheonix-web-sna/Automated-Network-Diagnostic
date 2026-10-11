"""
collector.py — IntelliNet Data Collection Orchestrator

Assembles a complete DiagnosticResult from all probe modules.
Called by the GUI and monitoring worker for one shared diagnostic sequence.
Also provides build_diagnostic_result() for typed result assembly.
"""

import sys
import os
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    DiagnosticResult, AdapterInfo, IPInfo, GatewayInfo,
    WiFiInfo, DNSInfo, InternetInfo, PerformanceMetrics,
    HealthScore, RCAResult, Recommendation
)
import config as cfg
import network_diagnostics as nd
import performance as perf
import rca_engine
import recommendations as rec_engine


def _internet_probe_target(details: str):
    """Extract the host that actually answered the reachability probe."""
    icmp_match = re.search(r"ICMP reachable \(([^)]+)\)", details, re.IGNORECASE)
    if icmp_match:
        return icmp_match.group(1), "ICMP"
    tcp_match = re.search(r"TCP connected \(([^:()]+):\d+\)", details, re.IGNORECASE)
    if tcp_match:
        return tcp_match.group(1), "TCP"
    return cfg.PING_TARGET_PRIMARY, ""


def build_diagnostic_result(
    adapter_tuple:  tuple,
    ip_tuple:       tuple,
    gateway_tuple:  tuple,
    wifi_info:      WiFiInfo,
    dns_tuple:      tuple,
    internet_tuple: tuple,
    perf_metrics:   PerformanceMetrics,
) -> DiagnosticResult:
    """
    Convert raw probe tuples + WiFiInfo + PerformanceMetrics into a DiagnosticResult.

    Used by collect_diagnostic() after it has emitted the individual live steps.

    Args:
        adapter_tuple  : (is_up: bool, name: str, display: str)
        ip_tuple       : (is_valid: bool, ip: str, display: str)
        gateway_tuple  : (has_gw: bool, gw_ip: str, is_reachable: bool, display: str)
        wifi_info      : WiFiInfo dataclass from nd.get_wifi_info()
        dns_tuple      : (is_working: bool, status_str: str, details: str)
        internet_tuple : (is_connected: bool, status_str: str, details: str)
        perf_metrics   : PerformanceMetrics from performance.measure_performance()

    Returns:
        DiagnosticResult with health, rca, and recommendation computed.
    """
    # ── Unpack tuples into typed dataclasses ──────────────────────────────
    adapter_ok, adapter_name, adapter_det = adapter_tuple
    ip_ok, ip_addr, ip_det               = ip_tuple
    gw_has, gw_ip, gw_reachable, gw_disp = gateway_tuple
    dns_ok, dns_status, dns_det          = dns_tuple
    inet_ok, inet_status, inet_det       = internet_tuple

    # Determine adapter type from name
    atype = "Unknown"
    name_lower = adapter_name.lower()
    if any(k in name_lower for k in ("wi-fi", "wifi", "wlan", "wireless")):
        atype = "Wi-Fi"
    elif any(k in name_lower for k in ("ethernet", "lan", "local area")):
        atype = "Ethernet"

    # Extract MAC address, link speed, and subnet mask from psutil if available
    mac_addr = ""
    speed_mbps = 0
    subnet_mask = ""
    try:
        import psutil
        import socket
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        if adapter_name in addrs:
            for addr in addrs[adapter_name]:
                if hasattr(psutil, "AF_LINK") and addr.family == psutil.AF_LINK:
                    mac_addr = addr.address
                elif addr.family == socket.AF_INET:
                    subnet_mask = addr.netmask or ""
        if adapter_name in stats:
            speed_mbps = stats[adapter_name].speed or 0
    except Exception:
        pass

    adapter = AdapterInfo(
        is_up=adapter_ok,
        name=adapter_name,
        display=adapter_det,
        adapter_type=atype,
        speed_mbps=speed_mbps,
        mac_address=mac_addr,
    )

    ip = IPInfo(
        is_valid=ip_ok,
        ipv4=ip_addr,
        subnet_mask=subnet_mask,
        display=ip_det,
    )

    gateway = GatewayInfo(
        has_gateway=gw_has,
        ip=gw_ip,
        is_reachable=gw_reachable,
        display=gw_disp,
    )

    resolved_match = re.search(r"\bResolved\b.*?->\s*([0-9.]+)", dns_det, re.IGNORECASE)
    dns = DNSInfo(
        is_working=dns_ok,
        domain_tested=cfg.DNS_TEST_DOMAIN,
        resolved_ip=resolved_match.group(1) if resolved_match else "",
        display=dns_det,
        dns_servers=nd.get_dns_servers(adapter_name if adapter_ok else None),
    )

    internet_target, internet_method = _internet_probe_target(inet_det)
    internet = InternetInfo(
        is_connected=inet_ok,
        target_ip=internet_target,
        method=internet_method,
        display=inet_det,
    )

    # Interface stats counters
    iface_stats = nd.get_interface_stats(adapter_name) if adapter_ok else {}

    # ── Temporary DiagnosticResult for engine input ────────────────────────
    # health/rca/recommendation are placeholders; computed below
    _placeholder_health = HealthScore(score=0)
    _placeholder_rca    = RCAResult(
        case_code="", primary_cause="", secondary_causes=[],
        confidence=0, overall_status="", severity="")
    _placeholder_rec    = Recommendation(
        severity="", summary="", steps=[], case_code="")

    result = DiagnosticResult(
        timestamp=datetime.now(),
        adapter=adapter,
        ip=ip,
        gateway=gateway,
        wifi=wifi_info,
        dns=dns,
        internet=internet,
        performance=perf_metrics,
        health=_placeholder_health,
        rca=_placeholder_rca,
        recommendation=_placeholder_rec,
        interface_stats=iface_stats,
    )

    # ── Compute Health Score ───────────────────────────────────────────────
    result.health = rca_engine.calculate_health_score(result)

    # ── Root Cause Analysis ────────────────────────────────────────────────
    result.rca = rca_engine.analyze(result)

    # ── Recommendation Engine ─────────────────────────────────────────────
    result.recommendation = rec_engine.get_recommendation(result.rca)

    return result


def collect_diagnostic(progress_callback=None) -> DiagnosticResult:
    """
    Run the shared diagnostic sequence and return a complete result.

    The optional callback receives:
      (row, headline, status, symbol, details, tag, log_message, percent)
    """
    def emit(row, headline, status, symbol, details, tag, message, percent):
        if progress_callback:
            progress_callback(row, headline, status, symbol, details, tag, message, percent)

    adapter_tuple = nd.get_active_adapter()
    adapter_ok, adapter_name, adapter_details = adapter_tuple
    emit(
        0, "Detecting network adapter...", "Active" if adapter_ok else "Failed",
        "✓" if adapter_ok else "✗", adapter_details,
        "pass" if adapter_ok else "fail",
        f"Step 1: Network Adapter -> {adapter_name} ({'UP' if adapter_ok else 'DOWN'})",
        10,
    )

    ip_tuple = (
        nd.get_ipv4_address(adapter_name)
        if adapter_ok
        else (False, "Not Available", "No active adapter")
    )
    ip_ok, ip_addr, ip_details = ip_tuple
    emit(
        1, "Detecting IPv4 configuration...", "Assigned" if ip_ok else "Failed",
        "✓" if ip_ok else "✗", ip_details,
        "pass" if ip_ok else "fail", f"Step 2: IPv4 Address -> {ip_addr}", 24,
    )

    gateway_tuple = nd.check_gateway(adapter_name if adapter_ok else None)
    gw_has, gw_ip, gw_reachable, gw_details = gateway_tuple
    emit(
        2, "Checking default gateway reachability...",
        "Reachable" if gw_has and gw_reachable else "Unreachable",
        "✓" if gw_has and gw_reachable else "✗", gw_details,
        "pass" if gw_has and gw_reachable else ("warn" if gw_has else "fail"),
        f"Step 3: Default Gateway -> {gw_ip} ({'Reachable' if gw_reachable else 'Unreachable'})",
        38,
    )

    wifi_info = nd.get_wifi_info()
    if wifi_info.is_wifi:
        wifi_status, wifi_symbol, wifi_tag = "Connected", "✓", "pass"
    elif adapter_ok and "ethernet" in adapter_name.lower():
        wifi_status, wifi_symbol, wifi_tag = "Wired", "ℹ", "info"
    else:
        wifi_status, wifi_symbol, wifi_tag = "Unavailable", "—", "muted"
    emit(
        3, "Querying Wi-Fi and physical link parameters...", wifi_status,
        wifi_symbol, wifi_info.display or wifi_status, wifi_tag,
        f"Step 4: Wi-Fi / Link -> {wifi_info.display or wifi_status}", 50,
    )

    dns_tuple = nd.check_dns(cfg.DNS_TEST_DOMAIN)
    dns_ok, dns_status, dns_details = dns_tuple
    emit(
        4, f"Resolving DNS ({cfg.DNS_TEST_DOMAIN})...", dns_status,
        "✓" if dns_ok else "✗", dns_details,
        "pass" if dns_ok else "fail",
        f"Step 5: DNS Resolution -> {dns_details}", 64,
    )

    internet_tuple = nd.check_internet(cfg.PING_TARGET_PRIMARY)
    inet_ok, inet_status, inet_details = internet_tuple
    emit(
        5, f"Testing internet connectivity ({cfg.PING_TARGET_PRIMARY})...", inet_status,
        "✓" if inet_ok else "✗", inet_details,
        "pass" if inet_ok else "fail",
        f"Step 6: Internet Access -> {inet_details}", 76,
    )

    # Measure Internet performance when available; otherwise measure the LAN gateway.
    if inet_ok:
        target, _ = _internet_probe_target(inet_details)
    elif gw_reachable:
        target = gw_ip
    else:
        target = ""
    perf_metrics = (
        perf.measure_performance(target, cfg.PING_COUNT, cfg.PING_TIMEOUT_MS)
        if target else
        PerformanceMetrics(
            avg_latency_ms=-1, min_latency_ms=-1, max_latency_ms=-1,
            jitter_ms=-1, packet_loss_pct=-1.0, ping_count=0,
            target_host="", error="No reachable host for performance test",
        )
    )

    if perf_metrics.is_valid:
        latency_status = f"{perf_metrics.avg_latency_ms:.0f} ms"
        latency_symbol = "✓" if perf_metrics.avg_latency_ms <= cfg.LATENCY_FAIR_MS else "⚠"
        latency_tag = "pass" if latency_symbol == "✓" else "warn"
        latency_details = perf_metrics.latency_display
    else:
        latency_status, latency_symbol, latency_tag = "N/A", "—", "muted"
        latency_details = perf_metrics.error or "Measurement unavailable"
    emit(
        6, "Measuring latency and packet loss...", latency_status,
        latency_symbol, latency_details, latency_tag,
        f"Step 7: Latency -> {latency_details}", 88,
    )

    if perf_metrics.has_packet_measurement:
        loss_status = f"{perf_metrics.packet_loss_pct:.0f}%"
        loss_symbol = "✓" if perf_metrics.packet_loss_pct <= cfg.LOSS_FAIR_PCT else "⚠"
        loss_tag = "pass" if loss_symbol == "✓" else "warn"
        loss_details = perf_metrics.loss_display
    else:
        loss_status, loss_symbol, loss_tag = "N/A", "—", "muted"
        loss_details = perf_metrics.error or "Measurement unavailable"
    emit(
        7, "Measuring latency and packet loss...", loss_status,
        loss_symbol, loss_details, loss_tag,
        f"Step 8: Packet Loss -> {loss_details}", 95,
    )

    result = build_diagnostic_result(
        adapter_tuple, ip_tuple, gateway_tuple,
        wifi_info, dns_tuple, internet_tuple, perf_metrics,
    )
    if progress_callback:
        progress_callback(None, "Diagnostic complete", "", "", "", "", "", 100)
    return result
