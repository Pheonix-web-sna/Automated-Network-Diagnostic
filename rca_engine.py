"""
rca_engine.py - IntelliNet Root Cause Analysis Engine

Evaluates all collected diagnostic data and produces:
  - Primary root cause identification
  - Secondary contributing factors
  - Confidence Score (0-100%) for the diagnosis
  - Health Score (0-100) composite network quality metric
  - Severity classification

Design:
  The engine uses a weighted symptom matrix, not a flat if/else chain.
  Each diagnostic layer is evaluated independently, then combined.
  A confidence penalty is applied when symptoms are ambiguous or contradictory.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import DiagnosticResult, RCAResult, HealthScore
import config as cfg


# ═══════════════════════════════════════════════════════════════
# HEALTH SCORE ENGINE
# ═══════════════════════════════════════════════════════════════

def calculate_health_score(result: DiagnosticResult) -> HealthScore:
    """
    Compute composite network Health Score (0-100).

    Component weights (from config.HEALTH_WEIGHTS):
      adapter      -> 20 pts   (binary: up / down)
      ip           -> 20 pts   (binary: valid / not valid)
      gateway      -> 20 pts   (binary: reachable / unreachable)
      dns          -> 15 pts   (binary: working / failed)
      internet     -> 15 pts   (binary: connected / unreachable)
      latency      ->  5 pts   (graduated: ≤30ms=5, ≤60=4, ≤100=3, ≤200=1, else=0)
      packet_loss  ->  5 pts   (graduated: 0%=5, ≤2%=3, ≤5%=1, else=0)
    """
    w = cfg.HEALTH_WEIGHTS
    score = 0
    components = {}

    # ── Binary components ──────────────────────────────────────────────────
    if result.adapter.is_up:
        components["adapter"] = w["adapter"]
        score += w["adapter"]
    else:
        components["adapter"] = 0

    if result.ip.is_valid:
        components["ip"] = w["ip"]
        score += w["ip"]
    else:
        components["ip"] = 0

    if result.gateway.is_reachable:
        components["gateway"] = w["gateway"]
        score += w["gateway"]
    else:
        components["gateway"] = 0

    if result.dns.is_working:
        components["dns"] = w["dns"]
        score += w["dns"]
    else:
        components["dns"] = 0

    if result.internet.is_connected:
        components["internet"] = w["internet"]
        score += w["internet"]
    else:
        components["internet"] = 0

    # ── Graduated: Latency ─────────────────────────────────────────────────
    lat = result.performance.avg_latency_ms
    if lat < 0:
        components["latency"] = 0   # Measurement unavailable
    elif lat <= cfg.LATENCY_EXCELLENT_MS:
        components["latency"] = w["latency"]             # 5 pts
        score += w["latency"]
    elif lat <= cfg.LATENCY_GOOD_MS:
        components["latency"] = int(w["latency"] * 0.8)  # 4 pts
        score += components["latency"]
    elif lat <= cfg.LATENCY_FAIR_MS:
        components["latency"] = int(w["latency"] * 0.6)  # 3 pts
        score += components["latency"]
    elif lat <= cfg.LATENCY_POOR_MS:
        components["latency"] = int(w["latency"] * 0.2)  # 1 pt
        score += components["latency"]
    else:
        components["latency"] = 0

    # ── Graduated: Packet Loss ─────────────────────────────────────────────
    loss = result.performance.packet_loss_pct
    if not result.performance.has_packet_measurement:
        components["packet_loss"] = 0   # Measurement unavailable
    elif loss <= cfg.LOSS_EXCELLENT_PCT:
        components["packet_loss"] = w["packet_loss"]             # 5 pts
        score += w["packet_loss"]
    elif loss <= cfg.LOSS_GOOD_PCT:
        components["packet_loss"] = int(w["packet_loss"] * 0.6)  # 3 pts
        score += components["packet_loss"]
    elif loss <= cfg.LOSS_FAIR_PCT:
        components["packet_loss"] = int(w["packet_loss"] * 0.2)  # 1 pt
        score += components["packet_loss"]
    else:
        components["packet_loss"] = 0

    return HealthScore(score=min(score, 100), components=components)


# ═══════════════════════════════════════════════════════════════
# CONFIDENCE SCORE ENGINE
# ═══════════════════════════════════════════════════════════════

def _confidence(case_code: str) -> int:
    """
    Calculate diagnostic confidence (0-100).

    Logic:
      - Single unambiguous point of failure -> high confidence (90-99).
      - Multiple simultaneous failures -> moderate (75-88).
      - Performance-only issues -> lower (70-80) because cause is harder to pinpoint.
      - All-normal -> 99.
      - Unknown state -> 60.
    """
    if case_code == "CASE_6":
        # Everything healthy
        return 99

    if case_code == "CASE_1":
        # Adapter down - completely unambiguous
        return 97

    if case_code == "CASE_2":
        # Adapter up but no IP - almost certainly DHCP failure or wrong adapter
        return 94

    if case_code == "CASE_3":
        # IP assigned but gateway unreachable
        # Could be: router down, cable unplugged, wrong gateway route, firewall
        # Slightly ambiguous - 4 possible root causes
        return 87

    if case_code == "CASE_4":
        # Gateway OK + Internet IP OK + DNS fails = pure DNS failure
        # High confidence because internet works (proves routing is fine)
        return 91

    if case_code == "CASE_5":
        # Gateway OK + DNS OK + Internet IP fails
        # DNS works means we can reach 8.8.8.8:53 (or DNS server), so some routing works
        # But ICMP/data blocked -> ISP, firewall, or ISP-level routing issue
        # Ambiguous between ISP and firewall
        return 79

    if case_code == "CASE_HYBRID":
        # Gateway OK + DNS fail + Internet IP fail
        # Clearly a WAN-side outage, but could be ISP or router WAN config
        return 85

    if case_code == "CASE_PERF":
        # Everything connected but degraded performance
        # Cause could be: congestion, bad line, ISP throttling, Wi-Fi interference
        return 72

    # Unknown / fallback
    return 60


# ═══════════════════════════════════════════════════════════════
# ROOT CAUSE ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════

def analyze(result: DiagnosticResult) -> RCAResult:
    """
    Evaluate DiagnosticResult and produce RCAResult with:
      - case_code
      - primary_cause (human-readable sentence)
      - secondary_causes (list of contributing factors)
      - confidence (0-100)
      - overall_status (display string)
      - severity ("CRITICAL", "WARNING", "PERFORMANCE", "NORMAL")

    Rule hierarchy follows OSI model bottom-up (Layer 2 -> Layer 3 -> Layer 4 -> Layer 7):
      L2: Adapter
      L3: IP, Gateway
      L4: Internet connectivity (ICMP / TCP)
      L7: DNS (application layer name resolution)
      Perf: Latency & Packet Loss
    """
    a_ok    = result.adapter.is_up
    ip_ok   = result.ip.is_valid
    gw_ok   = result.gateway.is_reachable
    dns_ok  = result.dns.is_working
    inet_ok = result.internet.is_connected
    perf    = result.performance

    secondary = []

    # ── CASE 1: No active adapter ──────────────────────────────────────────
    if not a_ok:
        return RCAResult(
            case_code="CASE_1",
            primary_cause="Network adapter is disconnected or disabled.",
            secondary_causes=["All connectivity layers are unavailable without an active adapter."],
            confidence=_confidence("CASE_1"),
            overall_status="CRITICAL - ADAPTER DISCONNECTED",
            severity="CRITICAL",
        )

    # ── CASE 2: Adapter up, no valid IP ──────────────────────────────────
    if not ip_ok:
        secondary = ["DHCP server may be unavailable.",
                     "Network cable may be unplugged (if Ethernet).",
                     "Wi-Fi authentication may have failed."]
        return RCAResult(
            case_code="CASE_2",
            primary_cause="No valid IPv4 address has been assigned to the active adapter.",
            secondary_causes=secondary,
            confidence=_confidence("CASE_2"),
            overall_status="CRITICAL - NO IP ASSIGNED",
            severity="CRITICAL",
        )

    # ── CASE 3: IP assigned, gateway unreachable ──────────────────────────
    if not gw_ok:
        secondary = ["Router may be powered off or restarting.",
                     "Ethernet cable between device and router may be faulty.",
                     "Wi-Fi channel congestion may be causing packet loss to the gateway."]
        if result.gateway.ip == "Not Available":
            secondary.insert(0, "No default gateway is configured on this interface.")
        return RCAResult(
            case_code="CASE_3",
            primary_cause="Local network gateway is unreachable.",
            secondary_causes=secondary,
            confidence=_confidence("CASE_3"),
            overall_status="WARNING - GATEWAY UNREACHABLE",
            severity="WARNING",
        )

    # ── From here, gateway is reachable. ──────────────────────────────────

    # ── CASE 4: Gateway OK + Internet OK + DNS fails ───────────────────────
    if gw_ok and inet_ok and not dns_ok:
        secondary = ["DNS server address may be incorrect.",
                     "ISP DNS server may be temporarily down.",
                     "Custom DNS (e.g. 8.8.8.8) may be blocked by a firewall."]
        return RCAResult(
            case_code="CASE_4",
            primary_cause="DNS name resolution is failing. Internet routing itself is functional.",
            secondary_causes=secondary,
            confidence=_confidence("CASE_4"),
            overall_status="WARNING - DNS RESOLUTION FAILURE",
            severity="WARNING",
        )

    # ── CASE 5: Gateway OK + DNS OK + Internet IP fails ────────────────────
    if gw_ok and dns_ok and not inet_ok:
        secondary = ["ISP may be experiencing a WAN-side outage.",
                     "Firewall or parental controls may be blocking ICMP traffic.",
                     "Router WAN port may have lost IP from ISP (PPPoE/DHCP failure)."]
        return RCAResult(
            case_code="CASE_5",
            primary_cause="Internet connectivity is unreachable despite functional local gateway and DNS.",
            secondary_causes=secondary,
            confidence=_confidence("CASE_5"),
            overall_status="WARNING - INTERNET UNREACHABLE",
            severity="WARNING",
        )

    # ── CASE HYBRID: Gateway OK + DNS fail + Internet IP fail ──────────────
    if gw_ok and not dns_ok and not inet_ok:
        secondary = ["ISP WAN connection may be offline.",
                     "Router may be connected to LAN but not to the internet.",
                     "PPPoE / DHCP lease from ISP may have expired."]
        return RCAResult(
            case_code="CASE_HYBRID",
            primary_cause="Local gateway is reachable, but all WAN Internet access (DNS and IP) is unavailable.",
            secondary_causes=secondary,
            confidence=_confidence("CASE_HYBRID"),
            overall_status="WARNING - WAN INTERNET DOWN",
            severity="WARNING",
        )

    # ── CASE 6: All connectivity layers pass ───────────────────────────────
    if gw_ok and dns_ok and inet_ok:
        # Check for performance degradation even though connected
        if perf.is_valid or perf.has_packet_measurement:
            has_latency_issue = perf.is_valid and perf.avg_latency_ms > cfg.LATENCY_FAIR_MS
            has_loss_issue = (
                perf.has_packet_measurement
                and perf.packet_loss_pct > cfg.LOSS_FAIR_PCT
            )

            if has_latency_issue or has_loss_issue:
                secondary = []
                if has_latency_issue:
                    secondary.append(f"High average latency: {perf.avg_latency_ms:.0f}ms (threshold: {cfg.LATENCY_FAIR_MS}ms).")
                if has_loss_issue:
                    if perf.packet_loss_pct >= 100:
                        secondary.append(
                            "No ICMP echo replies were received; the target may filter ICMP."
                        )
                    else:
                        secondary.append(
                            f"Elevated ICMP packet loss: {perf.packet_loss_pct:.0f}% "
                            f"(threshold: {cfg.LOSS_FAIR_PCT}%)."
                        )
                secondary.append("Possible causes: network congestion, Wi-Fi interference, or ISP throttling.")

                return RCAResult(
                    case_code="CASE_PERF",
                    primary_cause="Connected but experiencing degraded network performance.",
                    secondary_causes=secondary,
                    confidence=_confidence("CASE_PERF"),
                    overall_status="PERFORMANCE - DEGRADED QUALITY",
                    severity="PERFORMANCE",
                )

        # All clear - fully healthy
        return RCAResult(
            case_code="CASE_6",
            primary_cause="Network connection is functioning normally across all diagnostic layers.",
            secondary_causes=[],
            confidence=_confidence("CASE_6"),
            overall_status="NORMAL - FULLY OPERATIONAL",
            severity="NORMAL",
        )

    # ── DEFAULT FALLBACK ───────────────────────────────────────────────────
    return RCAResult(
        case_code="CASE_UNKNOWN",
        primary_cause="Inconsistent diagnostic data. Network state is indeterminate.",
        secondary_causes=["Run the diagnostic again to confirm.",
                          "Check for conflicting network adapters."],
        confidence=60,
        overall_status="UNKNOWN - INDETERMINATE STATE",
        severity="WARNING",
    )
