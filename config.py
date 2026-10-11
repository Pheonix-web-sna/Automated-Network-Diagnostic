"""
config.py — IntelliNet Configuration Layer
Centralized constants, thresholds, and settings.
No imports from other IntelliNet modules.
"""

# ── Application Identity ──────────────────────────────────────────────────────
APP_NAME = "IntelliNet"
APP_SUBTITLE = "Intelligent Network Health & Diagnostics System"
APP_VERSION = "2.0.0"

# ── Ping / Connectivity Targets ───────────────────────────────────────────────
PING_TARGET_PRIMARY   = "8.8.8.8"      # Google Public DNS (ICMP target)
PING_TARGET_SECONDARY = "1.1.1.1"      # Cloudflare DNS (fallback ICMP)
TCP_FALLBACK_HOST     = "8.8.8.8"
TCP_FALLBACK_PORT     = 53             # DNS port — almost never firewalled
TCP_FALLBACK_TIMEOUT_SEC = 2

# ── DNS Resolution Test ───────────────────────────────────────────────────────
DNS_TEST_DOMAIN           = "google.com"
DNS_SOCKET_TIMEOUT_SEC    = 3
DNS_SERVER_QUERY_TIMEOUT_SEC = 8
NETWORK_COMMAND_TIMEOUT_SEC = 6

# ── Ping Parameters ───────────────────────────────────────────────────────────
PING_COUNT          = 4       # Number of pings for performance measurement
PING_TIMEOUT_MS     = 2000    # Per-ping timeout (ms) passed to Windows ping -w
QUICK_PING_TIMEOUT  = 2       # Seconds for quick single-ping check
PING_QUICK_TIMEOUT_BUFFER_SEC = 3
PING_PROCESS_TIMEOUT_BUFFER_SEC = 4
JITTER_STABLE_MS    = 15
REMEDIATION_COMMAND_TIMEOUT_SEC = 60

# ── Latency Thresholds (ms) ───────────────────────────────────────────────────
LATENCY_EXCELLENT_MS  = 30
LATENCY_GOOD_MS       = 60
LATENCY_FAIR_MS       = 100
LATENCY_POOR_MS       = 200

# ── Packet Loss Thresholds (%) ────────────────────────────────────────────────
LOSS_EXCELLENT_PCT = 0
LOSS_GOOD_PCT      = 2
LOSS_FAIR_PCT      = 5
LOSS_POOR_PCT      = 10

# ── Health Score Weights (must sum to 100) ────────────────────────────────────
HEALTH_WEIGHTS = {
    "adapter":      20,
    "ip":           20,
    "gateway":      20,
    "dns":          15,
    "internet":     15,
    "latency":       5,
    "packet_loss":   5,
}

# ── Window Geometry ───────────────────────────────────────────────────────────
WINDOW_WIDTH      = 1180
WINDOW_HEIGHT     = 820
WINDOW_MIN_WIDTH  = 1020
WINDOW_MIN_HEIGHT = 700

# ── Color Palette ─────────────────────────────────────────────────────────────
COLOR_BG           = "#0F172A"   # Main background (deep navy)
COLOR_PANEL        = "#1E293B"   # Panel / card background
COLOR_PANEL_ALT    = "#334155"   # Secondary panel / dividers
COLOR_PANEL_DARK   = "#0B1120"   # Darker variant for table headers
COLOR_SIDEBAR      = "#090D16"   # Deep sidebar background
COLOR_SIDEBAR_ACTIVE = "#1E293B" # Active navigation button bg
COLOR_ACCENT       = "#0EA5E9"   # Sky blue primary accent
COLOR_ACCENT_HOVER = "#0284C7"   # Hover state
COLOR_TEXT_PRIMARY = "#F8FAFC"   # Main text
COLOR_TEXT_MUTED   = "#94A3B8"   # Muted / secondary text
COLOR_SUCCESS      = "#22C55E"   # Green  — pass
COLOR_FAILURE      = "#EF4444"   # Red    — fail / critical
COLOR_WARNING      = "#F59E0B"   # Amber  — warning
COLOR_PURPLE       = "#8B5CF6"   # Purple — confidence score accent
COLOR_TEAL         = "#14B8A6"   # Teal   — performance metric accent

# ── Database / Storage (Phase 3) ──────────────────────────────────────────────
DB_FILENAME      = "intellinet.db"
DB_BUSY_TIMEOUT_SEC = 10
MAX_HISTORY_SESSIONS = 500
MAX_EVENT_LOG_ENTRIES = 1000
MAX_DIAGNOSTIC_LOG_LINES = 500
MAX_MONITOR_LOG_LINES = 500

# ── Monitoring Defaults ───────────────────────────────────────────────────────
MONITOR_DEFAULT_INTERVAL_SEC = 60     # Default scan interval in seconds
MONITOR_MIN_INTERVAL_SEC     = 30     # Minimum allowed interval
MONITOR_MAX_INTERVAL_SEC     = 600    # Maximum allowed interval
MONITOR_INTERVAL_OPTIONS = (30, 60, 120, 300, 600)

# ── Degradation Detection Thresholds ──────────────────────────────────────────
DEGRADE_HEALTH_DROP_PTS      = 15     # Alert if health drops > N pts vs avg
DEGRADE_LATENCY_INCREASE_PCT = 50     # Alert if latency increases > N% vs avg
DEGRADE_LOSS_INCREASE_PCT    = 3      # Alert if packet loss increases > N% vs avg
DEGRADE_WINDOW_SIZE          = 10     # Number of recent scans to compare against
