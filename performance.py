"""
performance.py — IntelliNet Performance Analyzer
Measures network latency, jitter, and packet loss using multi-ping.

Uses Windows native ping command (no external dependencies).
Does NOT use ping3 (requires admin; too fragile for classroom use).
"""

import subprocess
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import PerformanceMetrics
import config as cfg


def _unavailable(host: str, reason: str) -> PerformanceMetrics:
    """Return a sentinel PerformanceMetrics indicating measurement not possible."""
    return PerformanceMetrics(
        avg_latency_ms=-1,
        min_latency_ms=-1,
        max_latency_ms=-1,
        jitter_ms=-1,
        packet_loss_pct=-1.0,
        ping_count=0,
        target_host=host,
        error=reason,
    )


def _parse_ping_output(output: str, count: int, host: str) -> PerformanceMetrics:
    """
    Parse Windows ping output into PerformanceMetrics.

    Handles two formats:
      A. Summary statistics line:
         "Minimum = 5ms, Maximum = 12ms, Average = 7ms"
      B. Per-reply lines (fallback):
         "Reply from 8.8.8.8: bytes=32 time=8ms TTL=117"
    """
    # ── Packet loss ──────────────────────────────────────────────────────────
    # "Packets: Sent = 4, Received = 3, Lost = 1 (25% loss)"
    summary_m = re.search(
        r"Sent\s*=\s*(\d+)\s*,\s*Received\s*=\s*(\d+)\s*,\s*Lost\s*=\s*(\d+)",
        output,
        re.IGNORECASE,
    )
    if summary_m:
        sent = int(summary_m.group(1))
        received = int(summary_m.group(2))
        lost = int(summary_m.group(3))
        packet_loss = (lost / sent * 100) if sent else 100.0
    else:
        sent = count
        received = None
        loss_m = re.search(r"\((\d+(?:\.\d+)?)%\s*loss\)", output, re.IGNORECASE)
        packet_loss = float(loss_m.group(1)) if loss_m else None

    # ── Latency — Method A: summary line ────────────────────────────────────
    stats_m = re.search(
        r"Minimum\s*=\s*(\d+)ms.*?Maximum\s*=\s*(\d+)ms.*?Average\s*=\s*(\d+)ms",
        output, re.DOTALL | re.IGNORECASE,
    )
    if stats_m:
        min_ms  = float(stats_m.group(1))
        max_ms  = float(stats_m.group(2))
        avg_ms  = float(stats_m.group(3))
        jitter  = round(max_ms - min_ms, 1)
        return PerformanceMetrics(
            avg_latency_ms=round(avg_ms, 1),
            min_latency_ms=round(min_ms, 1),
            max_latency_ms=round(max_ms, 1),
            jitter_ms=jitter,
            packet_loss_pct=packet_loss if packet_loss is not None else 0.0,
            ping_count=sent,
            target_host=host,
        )

    # ── Latency — Method B: per-reply parsing ────────────────────────────────
    # Matches "time=8ms" or "time<1ms"
    rtts = re.findall(r"time[=<](\d+)ms", output, re.IGNORECASE)
    if rtts:
        vals   = [int(r) for r in rtts]
        if received is None:
            received = len(vals)
        if packet_loss is None and sent > 0:
            packet_loss = max(0.0, (sent - received) / sent * 100)
        avg_ms = sum(vals) / len(vals)
        min_ms = float(min(vals))
        max_ms = float(max(vals))
        return PerformanceMetrics(
            avg_latency_ms=round(avg_ms, 1),
            min_latency_ms=round(min_ms, 1),
            max_latency_ms=round(max_ms, 1),
            jitter_ms=round(max_ms - min_ms, 1),
            packet_loss_pct=packet_loss if packet_loss is not None else 0.0,
            ping_count=sent,
            target_host=host,
        )

    # A completed sequence with no replies still provides a real 100% loss
    # measurement even though latency itself is unavailable.
    if sent > 0 and (packet_loss is not None or summary_m):
        if packet_loss is None:
            packet_loss = 100.0
        return PerformanceMetrics(
            avg_latency_ms=-1,
            min_latency_ms=-1,
            max_latency_ms=-1,
            jitter_ms=-1,
            packet_loss_pct=packet_loss,
            ping_count=sent,
            target_host=host,
            error="No ICMP echo replies received; the target may filter ICMP.",
        )

    # Completely failed — no packet summary and no RTT data found.
    return _unavailable(host, "No RTT data in ping output")


def measure_performance(
    host: str,
    count: int = cfg.PING_COUNT,
    timeout_ms: int = cfg.PING_TIMEOUT_MS,
) -> PerformanceMetrics:
    """
    Run `count` pings to `host` and return latency / packet-loss metrics.

    Args:
        host:       Target IP or hostname.
        count:      Number of ping packets (default 4 from config).
        timeout_ms: Per-packet timeout in ms (default 2000ms).

    Returns:
        PerformanceMetrics dataclass.
    """
    if not host or host in ("Not Available", "None", ""):
        return _unavailable(host, "No valid host to ping")

    try:
        # Total subprocess timeout = per-packet timeout * count + buffer
        total_timeout = int(
            (timeout_ms / 1000 + 0.5) * count + cfg.PING_PROCESS_TIMEOUT_BUFFER_SEC
        )
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

        cmd = ["ping", "-n", str(count), "-w", str(timeout_ms), host]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=total_timeout,
            creationflags=flags,
        )

        if not result.stdout.strip():
            return _unavailable(host, "Ping returned no output")

        return _parse_ping_output(result.stdout, count, host)

    except subprocess.TimeoutExpired:
        return _unavailable(host, "Ping subprocess timed out")
    except FileNotFoundError:
        return _unavailable(host, "ping command not found")
    except Exception as e:
        return _unavailable(host, str(e))
