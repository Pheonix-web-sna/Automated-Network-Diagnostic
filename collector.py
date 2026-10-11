"""
collector.py — IntelliNet Data Collection Orchestrator

Assembles a complete DiagnosticResult from all probe modules.
Called by main.py after each individual check completes (for live UI updates).
Also provides build_diagnostic_result() to assemble from pre-collected tuples.
"""

import sys
import os
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

    This is called from main.py AFTER all individual live-update steps are done,
    so the user has already seen each row update in real time.

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

    dns = DNSInfo(
        is_working=dns_ok,
        domain_tested=cfg.DNS_TEST_DOMAIN,
        display=dns_det,
        dns_servers=nd.get_dns_servers(adapter_name if adapter_ok else None),
    )

    internet = InternetInfo(
        is_connected=inet_ok,
        target_ip=cfg.PING_TARGET_PRIMARY,
        display=inet_det,
    )

    # Interface stats counters
    iface_stats = nd.get_interface_stats(adapter_name if adapter_ok else None)

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


def collect_diagnostic() -> DiagnosticResult:
    """
    Full single-call collection: runs all probes sequentially and returns
    a complete DiagnosticResult.

    Note: main.py uses the individual probe functions directly for live row updates.
    This function is provided for CLI use or future API integration.
    """
    adapter_tuple  = nd.get_active_adapter()
    ip_tuple       = nd.get_ipv4_address(adapter_tuple[1] if adapter_tuple[0] else None)
    gateway_tuple  = nd.check_gateway()
    wifi_info      = nd.get_wifi_info()
    dns_tuple      = nd.check_dns(cfg.DNS_TEST_DOMAIN)
    internet_tuple = nd.check_internet(cfg.PING_TARGET_PRIMARY)

    # Measure performance against internet IP if reachable, else gateway
    if internet_tuple[0]:
        target = cfg.PING_TARGET_PRIMARY
    elif gateway_tuple[2]:
        target = gateway_tuple[1]
    else:
        target = ""

    perf_metrics = (
        perf.measure_performance(target, cfg.PING_COUNT, cfg.PING_TIMEOUT_MS)
        if target else
        PerformanceMetrics(
            avg_latency_ms=-1, min_latency_ms=-1, max_latency_ms=-1,
            jitter_ms=-1, packet_loss_pct=100.0, ping_count=0,
            target_host="", error="No reachable host for performance test"
        )
    )

    return build_diagnostic_result(
        adapter_tuple, ip_tuple, gateway_tuple,
        wifi_info, dns_tuple, internet_tuple, perf_metrics
    )
