"""
db_manager.py — IntelliNet Database Manager (Phase 3)

SQLite storage layer for:
  - Diagnostic session history (full snapshots)
  - Health score history (time series)
  - Latency history (time series)
  - Packet-loss history (time series)
  - DNS response history (time series)
  - Network event log (timestamped entries)

Thread-safe: each method opens and closes its own connection.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg
from models import DiagnosticResult


# ── Database path ─────────────────────────────────────────────────────────────
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "intellinet.db")


def _get_conn() -> sqlite3.Connection:
    """Create and return a new SQLite connection with WAL mode."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they do not exist."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS diagnostic_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT    NOT NULL,
                adapter_name    TEXT,
                adapter_type    TEXT,
                adapter_up      INTEGER,
                ip_address      TEXT,
                subnet_mask     TEXT,
                gateway_ip      TEXT,
                gateway_reachable INTEGER,
                dns_working     INTEGER,
                dns_domain      TEXT,
                internet_connected INTEGER,
                wifi_ssid       TEXT,
                wifi_signal     INTEGER,
                avg_latency_ms  REAL,
                min_latency_ms  REAL,
                max_latency_ms  REAL,
                jitter_ms       REAL,
                packet_loss_pct REAL,
                ping_count      INTEGER,
                health_score    INTEGER,
                health_components TEXT,
                rca_case_code   TEXT,
                rca_primary     TEXT,
                rca_secondary   TEXT,
                rca_confidence  INTEGER,
                rca_severity    TEXT,
                rca_status      TEXT,
                rec_summary     TEXT,
                rec_steps       TEXT
            );

            CREATE TABLE IF NOT EXISTS health_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                score       INTEGER NOT NULL,
                label       TEXT
            );

            CREATE TABLE IF NOT EXISTS latency_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                avg_ms      REAL,
                min_ms      REAL,
                max_ms      REAL,
                jitter_ms   REAL
            );

            CREATE TABLE IF NOT EXISTS packet_loss_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                loss_pct    REAL,
                ping_count  INTEGER
            );

            CREATE TABLE IF NOT EXISTS dns_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                domain      TEXT,
                is_working  INTEGER,
                resolved_ip TEXT
            );

            CREATE TABLE IF NOT EXISTS event_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                severity    TEXT NOT NULL DEFAULT 'INFO',
                message     TEXT NOT NULL,
                details     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_health_ts ON health_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_latency_ts ON latency_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_loss_ts ON packet_loss_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_dns_ts ON dns_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_event_ts ON event_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_session_ts ON diagnostic_sessions(timestamp);
        """)
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# INSERT OPERATIONS
# ═══════════════════════════════════════════════════════════════

def save_diagnostic(result: DiagnosticResult) -> int:
    """
    Save a full DiagnosticResult snapshot and insert into all time-series tables.
    Returns the session ID.
    """
    ts = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    try:
        cur = conn.execute("""
            INSERT INTO diagnostic_sessions (
                timestamp, adapter_name, adapter_type, adapter_up,
                ip_address, subnet_mask, gateway_ip, gateway_reachable,
                dns_working, dns_domain, internet_connected,
                wifi_ssid, wifi_signal,
                avg_latency_ms, min_latency_ms, max_latency_ms,
                jitter_ms, packet_loss_pct, ping_count,
                health_score, health_components,
                rca_case_code, rca_primary, rca_secondary, rca_confidence,
                rca_severity, rca_status,
                rec_summary, rec_steps
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            ts,
            result.adapter.name,
            result.adapter.adapter_type,
            int(result.adapter.is_up),
            result.ip.ipv4,
            result.ip.subnet_mask,
            result.gateway.ip,
            int(result.gateway.is_reachable),
            int(result.dns.is_working),
            result.dns.domain_tested,
            int(result.internet.is_connected),
            result.wifi.ssid if result.wifi.is_wifi else "",
            result.wifi.signal_pct if result.wifi.is_wifi else -1,
            result.performance.avg_latency_ms,
            result.performance.min_latency_ms,
            result.performance.max_latency_ms,
            result.performance.jitter_ms,
            result.performance.packet_loss_pct,
            result.performance.ping_count,
            result.health.score,
            json.dumps(result.health.components),
            result.rca.case_code,
            result.rca.primary_cause,
            json.dumps(result.rca.secondary_causes),
            result.rca.confidence,
            result.rca.severity,
            result.rca.overall_status,
            result.recommendation.summary,
            json.dumps(result.recommendation.steps),
        ))
        session_id = cur.lastrowid

        # ── Time-series inserts ────────────────────────────────────────
        conn.execute(
            "INSERT INTO health_history (timestamp, score, label) VALUES (?,?,?)",
            (ts, result.health.score, result.health.label),
        )

        conn.execute(
            "INSERT INTO latency_history (timestamp, avg_ms, min_ms, max_ms, jitter_ms) VALUES (?,?,?,?,?)",
            (ts, result.performance.avg_latency_ms,
             result.performance.min_latency_ms,
             result.performance.max_latency_ms,
             result.performance.jitter_ms),
        )

        conn.execute(
            "INSERT INTO packet_loss_history (timestamp, loss_pct, ping_count) VALUES (?,?,?)",
            (ts, result.performance.packet_loss_pct, result.performance.ping_count),
        )

        conn.execute(
            "INSERT INTO dns_history (timestamp, domain, is_working, resolved_ip) VALUES (?,?,?,?)",
            (ts, result.dns.domain_tested, int(result.dns.is_working),
             result.dns.resolved_ip if hasattr(result.dns, 'resolved_ip') else ""),
        )

        conn.commit()
        return session_id

    finally:
        conn.close()


def log_event(event_type: str, message: str, severity: str = "INFO", details: str = ""):
    """Insert a network event into the event log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO event_log (timestamp, event_type, severity, message, details) VALUES (?,?,?,?,?)",
            (ts, event_type, severity, message, details),
        )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# QUERY OPERATIONS
# ═══════════════════════════════════════════════════════════════

def get_recent_sessions(limit: int = 50) -> List[Dict]:
    """Fetch most recent diagnostic sessions."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM diagnostic_sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_health_history(limit: int = 100) -> List[Dict]:
    """Fetch health score time-series data."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT timestamp, score, label FROM health_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def get_latency_history(limit: int = 100) -> List[Dict]:
    """Fetch latency time-series data."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT timestamp, avg_ms, min_ms, max_ms, jitter_ms FROM latency_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def get_packet_loss_history(limit: int = 100) -> List[Dict]:
    """Fetch packet loss time-series data."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT timestamp, loss_pct, ping_count FROM packet_loss_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def get_dns_history(limit: int = 100) -> List[Dict]:
    """Fetch DNS resolution history."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT timestamp, domain, is_working, resolved_ip FROM dns_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def get_event_log(limit: int = 200) -> List[Dict]:
    """Fetch recent event log entries (newest first)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT timestamp, event_type, severity, message, details FROM event_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session_count() -> int:
    """Return total number of diagnostic sessions stored."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM diagnostic_sessions").fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_event_count() -> int:
    """Return total number of events in the log."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM event_log").fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# DEGRADATION DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_degradation(current_result: DiagnosticResult, window: int = 10) -> List[str]:
    """
    Compare current diagnostic result against recent history to detect degradation.

    Checks:
      1. Health score dropped >15 points from average of last N sessions.
      2. Latency increased >50% from average.
      3. Packet loss increased >3% from average.
      4. DNS resolution started failing when it was working.

    Returns:
        List of degradation alert messages (empty = no degradation detected).
    """
    alerts = []

    # Health score comparison
    health_data = get_health_history(limit=window)
    if len(health_data) >= 3:
        avg_health = sum(d["score"] for d in health_data) / len(health_data)
        current_health = current_result.health.score
        drop = avg_health - current_health
        if drop > 15:
            alerts.append(
                f"Health score dropped to {current_health} "
                f"(avg of last {len(health_data)} scans: {avg_health:.0f}, drop: {drop:.0f} pts)"
            )

    # Latency comparison
    latency_data = get_latency_history(limit=window)
    valid_latencies = [d["avg_ms"] for d in latency_data if d["avg_ms"] is not None and d["avg_ms"] >= 0]
    if valid_latencies and current_result.performance.is_valid:
        avg_lat = sum(valid_latencies) / len(valid_latencies)
        cur_lat = current_result.performance.avg_latency_ms
        if avg_lat > 0 and cur_lat > avg_lat * 1.5:
            alerts.append(
                f"Latency spike detected: {cur_lat:.0f}ms "
                f"(historical avg: {avg_lat:.0f}ms, +{((cur_lat - avg_lat)/avg_lat)*100:.0f}%)"
            )

    # Packet loss comparison
    loss_data = get_packet_loss_history(limit=window)
    valid_losses = [d["loss_pct"] for d in loss_data if d["loss_pct"] is not None]
    if valid_losses and current_result.performance.is_valid:
        avg_loss = sum(valid_losses) / len(valid_losses)
        cur_loss = current_result.performance.packet_loss_pct
        if cur_loss > avg_loss + 3:
            alerts.append(
                f"Packet loss increased: {cur_loss:.0f}% "
                f"(historical avg: {avg_loss:.1f}%)"
            )

    # DNS regression
    dns_data = get_dns_history(limit=window)
    recent_dns_ok = [d["is_working"] for d in dns_data]
    if recent_dns_ok and not current_result.dns.is_working:
        ok_count = sum(recent_dns_ok)
        if ok_count > len(recent_dns_ok) * 0.7:
            alerts.append(
                f"DNS resolution failure detected (was working in {ok_count}/{len(recent_dns_ok)} recent scans)"
            )

    return alerts


# ═══════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════

# Auto-initialize database on import
init_db()
