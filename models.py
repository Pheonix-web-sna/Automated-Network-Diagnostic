"""
models.py — IntelliNet Data Model Layer
All dataclasses used across the IntelliNet engine.
No imports from other IntelliNet modules (zero circular dependency).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class AdapterInfo:
    """Network adapter detection result."""
    is_up: bool
    name: str           # e.g. "Wi-Fi", "Ethernet"
    display: str        # Human-readable display string
    adapter_type: str = ""   # "Wi-Fi", "Ethernet", "Other"
    speed_mbps: int = 0
    mac_address: str = ""


@dataclass
class IPInfo:
    """IPv4 address detection result."""
    is_valid: bool
    ipv4: str           # e.g. "172.16.16.86" or "Not Available"
    subnet_mask: str = ""
    display: str = ""


@dataclass
class GatewayInfo:
    """Default gateway detection and reachability result."""
    has_gateway: bool
    ip: str             # e.g. "172.16.0.1" or "Not Available"
    is_reachable: bool
    display: str = ""


@dataclass
class WiFiInfo:
    """Wi-Fi interface details from netsh wlan on Windows."""
    is_wifi: bool           # False if connected via Ethernet or not connected
    ssid: str = ""
    signal_pct: int = -1    # -1 = unknown
    radio_type: str = ""    # e.g. "802.11ax"
    channel: str = ""
    bssid: str = ""
    receive_rate_mbps: float = -1.0
    transmit_rate_mbps: float = -1.0
    display: str = ""       # Formatted for table display


@dataclass
class DNSInfo:
    """DNS resolution test result."""
    is_working: bool
    domain_tested: str
    resolved_ip: str = ""
    display: str = ""
    dns_servers: List[str] = field(default_factory=list)


@dataclass
class InternetInfo:
    """Internet connectivity test result (via direct IP ping, no DNS)."""
    is_connected: bool
    target_ip: str
    method: str = ""    # "ICMP" or "TCP"
    display: str = ""


@dataclass
class PerformanceMetrics:
    """
    Multi-ping latency and packet loss measurements.
    avg_latency_ms = -1 signals measurement unavailable.
    """
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    jitter_ms: float
    packet_loss_pct: float
    ping_count: int
    target_host: str
    error: str = ""

    @property
    def is_valid(self) -> bool:
        return self.avg_latency_ms >= 0

    @property
    def latency_display(self) -> str:
        if not self.is_valid:
            return "N/A"
        return (
            f"Avg: {self.avg_latency_ms:.0f}ms  "
            f"Min: {self.min_latency_ms:.0f}ms  "
            f"Max: {self.max_latency_ms:.0f}ms  "
            f"Jitter: {self.jitter_ms:.0f}ms"
        )

    @property
    def loss_display(self) -> str:
        if not self.is_valid:
            return "N/A"
        received = round(self.ping_count * (1 - self.packet_loss_pct / 100))
        lost = self.ping_count - received
        return f"{self.packet_loss_pct:.0f}%  ({received}/{self.ping_count} received, {lost} lost)"

    @property
    def latency_rating(self) -> str:
        """Qualitative rating for display."""
        if not self.is_valid:
            return "Unknown"
        lat = self.avg_latency_ms
        if lat <= 30:
            return "Excellent"
        elif lat <= 60:
            return "Good"
        elif lat <= 100:
            return "Fair"
        elif lat <= 200:
            return "Poor"
        else:
            return "Very Poor"


@dataclass
class HealthScore:
    """Composite network health score (0–100)."""
    score: int
    components: Dict[str, int] = field(default_factory=dict)

    @property
    def label(self) -> str:
        if self.score >= 90:
            return "Excellent"
        elif self.score >= 75:
            return "Good"
        elif self.score >= 50:
            return "Fair"
        elif self.score >= 25:
            return "Poor"
        else:
            return "Critical"

    @property
    def color(self) -> str:
        """Hex color code matching the score tier."""
        if self.score >= 80:
            return "#22C55E"    # Green
        elif self.score >= 55:
            return "#F59E0B"    # Amber
        else:
            return "#EF4444"    # Red


@dataclass
class RCAResult:
    """Root Cause Analysis engine output."""
    case_code: str
    primary_cause: str
    secondary_causes: List[str]
    confidence: int         # 0–100 — how certain we are about the root cause
    overall_status: str     # e.g. "CRITICAL", "WARNING - DNS", "NORMAL"
    severity: str           # "CRITICAL", "WARNING", "PERFORMANCE", "NORMAL"


@dataclass
class Recommendation:
    """Actionable recommendation produced by the Recommendation Engine."""
    severity: str
    summary: str
    steps: List[str]        # Numbered step-by-step fix instructions
    case_code: str


@dataclass
class DiagnosticResult:
    """
    Complete IntelliNet diagnostic session result.
    Assembled by collector.py, enriched by rca_engine.py and recommendations.py.
    """
    timestamp: datetime
    adapter: AdapterInfo
    ip: IPInfo
    gateway: GatewayInfo
    wifi: WiFiInfo
    dns: DNSInfo
    internet: InternetInfo
    performance: PerformanceMetrics
    health: HealthScore
    rca: RCAResult
    recommendation: Recommendation
    interface_stats: Dict[str, int] = field(default_factory=dict)
