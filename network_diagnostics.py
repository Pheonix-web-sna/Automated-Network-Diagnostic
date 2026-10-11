"""
network_diagnostics.py — IntelliNet Network Probe Layer
Extended for IntelliNet Phase 1.

Changes from original:
  - Fixed: socket.setdefaulttimeout() global call removed; per-socket timeouts used instead.
  - Fixed: route print used as PRIMARY gateway method (language-independent); ipconfig as fallback.
  - Added: get_wifi_info()       — SSID, signal strength, radio type via netsh wlan
  - Added: get_interface_stats() — bytes sent/received deltas via psutil
  - Preserved: all original function signatures for backward compatibility.
"""

import subprocess
import socket
import re
import time
import json
import psutil
import sys
import os

# Allow running standalone or as part of the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import WiFiInfo
import config as cfg


# ── Subprocess helper ────────────────────────────────────────────────────────

def _run_cmd(cmd: list, timeout: int = 6) -> str:
    """Run a Windows command silently and return stdout as string."""
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=flags,
        )
        return result.stdout
    except Exception:
        return ""


# ── 1. Adapter Detection ──────────────────────────────────────────────────────

def get_active_adapter():
    """
    Detect available network interfaces using psutil.
    Identifies active physical adapters (Wi-Fi, Ethernet).

    Returns:
        (is_connected: bool, adapter_name: str, details: str)
    """
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        active_adapters = []
        priority_keywords = ["wi-fi", "wifi", "ethernet", "wlan", "lan", "local area connection"]

        for iface_name, iface_stats in stats.items():
            if not iface_stats.isup:
                continue
            if "loopback" in iface_name.lower():
                continue
            if iface_name in addrs:
                for addr in addrs[iface_name]:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        if not ip.startswith("127."):
                            active_adapters.append((iface_name, ip))

        if not active_adapters:
            # Fallback: interface UP but no IP yet
            for iface_name, iface_stats in stats.items():
                if iface_stats.isup and "loopback" not in iface_name.lower():
                    return (True, iface_name, f"Connected ({iface_name})")
            return (False, "None", "No active network adapter detected")

        # Prefer Wi-Fi or Ethernet by keyword priority
        best = active_adapters[0][0]
        for iface_name, _ in active_adapters:
            if any(kw in iface_name.lower() for kw in priority_keywords):
                best = iface_name
                break

        return (True, best, best)

    except Exception as e:
        return (False, "Error", f"Adapter check failed: {str(e)}")


# ── 2. IP Address Detection ───────────────────────────────────────────────────

def get_ipv4_address(adapter_name=None):
    """
    Find IPv4 address for the active adapter.
    Excludes loopback (127.x.x.x) and APIPA (169.254.x.x) addresses.

    Returns:
        (has_ip: bool, ip_address: str, details: str)
    """
    try:
        addrs = psutil.net_if_addrs()

        if adapter_name and adapter_name in addrs:
            for addr in addrs[adapter_name]:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if not ip.startswith("127.") and not ip.startswith("169.254."):
                        return (True, ip, ip)
                    elif ip.startswith("169.254."):
                        return (False, "Not Available", f"APIPA Self-Assigned IP ({ip})")

        # Fallback: search all non-loopback adapters
        for iface_name, addr_list in addrs.items():
            if "loopback" in iface_name.lower():
                continue
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if not ip.startswith("127.") and not ip.startswith("169.254."):
                        return (True, ip, ip)

        return (False, "Not Available", "No valid IPv4 address assigned")

    except Exception as e:
        return (False, "Not Available", f"IP check error: {str(e)}")


# ── 3. Default Gateway Detection ──────────────────────────────────────────────

def get_default_gateway():
    """
    Determine default gateway.

    Method 1 (primary): route print 0.0.0.0 — language-independent numeric output.
    Method 2 (fallback): ipconfig — works on English Windows.

    Returns:
        gateway_ip: str or None
    """
    try:
        # PRIMARY: route print — language-independent
        out = _run_cmd(["route", "print", "0.0.0.0"], timeout=6)
        matches = re.findall(r"0\.0\.0\.0\s+0\.0\.0\.0\s+([\d\.]+)", out)
        valid = [g for g in matches if g not in ("0.0.0.0",) and not g.startswith("127.")]
        if valid:
            return valid[0]

        # FALLBACK: ipconfig (English Windows only)
        out2 = _run_cmd(["ipconfig"], timeout=6)
        matches2 = re.findall(r"Default Gateway[ .:]+(\d[\d\.]+)", out2)
        valid2 = [g for g in matches2 if g != "0.0.0.0" and not g.startswith("127.")]
        if valid2:
            return valid2[0]

    except Exception:
        pass

    return None


def get_dns_servers(adapter_name=None):
    """Return DNS server addresses configured on the selected Windows adapter."""
    if not adapter_name or sys.platform != "win32":
        return []

    # Interface names come from the local adapter inventory. Escape PowerShell's
    # single-quoted string delimiter before embedding the value in this read-only query.
    safe_name = str(adapter_name).replace("'", "''")
    script = (
        "$servers = Get-DnsClientServerAddress -AddressFamily IPv4 "
        f"| Where-Object {{ $_.InterfaceAlias -eq '{safe_name}' }} "
        "| Select-Object -ExpandProperty ServerAddresses; "
        "ConvertTo-Json -InputObject @($servers) -Compress"
    )
    output = _run_cmd(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=8,
    )
    try:
        values = json.loads(output)
    except (TypeError, ValueError):
        return []
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [str(value) for value in values if value]


def ping_host(host: str, timeout_sec: int = 2) -> bool:
    """
    Single ICMP ping using Windows ping command.

    Returns:
        True if host replies; False otherwise.
    """
    if not host or host in ("Not Available", "None"):
        return False
    try:
        timeout_ms = int(timeout_sec * 1000)
        out = _run_cmd(["ping", "-n", "1", "-w", str(timeout_ms), host],
                       timeout=timeout_sec + 3)
        out_lower = out.lower()
        return (
            "ttl=" in out_lower or
            "bytes=" in out_lower or
            "reply from" in out_lower
        ) and "unreachable" not in out_lower and "100% loss" not in out_lower
    except Exception:
        return False


def check_gateway():
    """
    Detect gateway and test reachability via ping.

    Returns:
        (has_gateway: bool, gateway_ip: str, is_reachable: bool, display_str: str)
    """
    gw = get_default_gateway()
    if not gw:
        return (False, "Not Available", False, "Not Available")
    reachable = ping_host(gw, timeout_sec=cfg.QUICK_PING_TIMEOUT)
    if reachable:
        return (True, gw, True, gw)
    else:
        return (True, gw, False, f"{gw} (Unreachable)")


# ── 4. DNS Resolution ────────────────────────────────────────────────────────

def check_dns(domain: str = "google.com"):
    """
    Test DNS resolution using a per-socket timeout (does NOT modify global socket timeout).

    Returns:
        (is_working: bool, status_str: str, details: str)
    """
    try:
        # getaddrinfo handles resolution without needing a socket object.
        # We avoid setdefaulttimeout() which is global and affects all sockets.
        result = socket.getaddrinfo(domain, None, socket.AF_INET,
                                    socket.SOCK_STREAM,
                                    0, socket.AI_ADDRCONFIG)
        if result:
            resolved_ip = result[0][4][0]
            return (True, "Working", f"Resolved {domain} -> {resolved_ip}")
        return (False, "Failed", f"No result for {domain}")
    except socket.gaierror:
        return (False, "Failed", f"Failed to resolve {domain}")
    except socket.timeout:
        return (False, "Failed", f"DNS timeout ({domain})")
    except Exception as e:
        return (False, "Failed", f"DNS error: {str(e)}")


# ── 5. Internet Connectivity ─────────────────────────────────────────────────

def check_internet(target_ip: str = cfg.PING_TARGET_PRIMARY):
    """
    Test internet connectivity via direct ICMP ping to a public IP (no DNS involved).
    Falls back to TCP on port 53 if ICMP is blocked.

    Returns:
        (is_connected: bool, status_str: str, details: str)
    """
    # Primary: ICMP ping
    if ping_host(target_ip, timeout_sec=cfg.QUICK_PING_TIMEOUT):
        return (True, "Connected", f"ICMP reachable ({target_ip})")

    # Secondary: try Cloudflare DNS IP
    secondary = cfg.PING_TARGET_SECONDARY
    if secondary != target_ip and ping_host(secondary, timeout_sec=cfg.QUICK_PING_TIMEOUT):
        return (True, "Connected", f"ICMP reachable ({secondary})")

    # TCP fallback (port 53 — DNS port on 8.8.8.8 is rarely blocked)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((cfg.TCP_FALLBACK_HOST, cfg.TCP_FALLBACK_PORT))
        s.close()
        return (True, "Connected", f"TCP connected ({cfg.TCP_FALLBACK_HOST}:{cfg.TCP_FALLBACK_PORT})")
    except Exception:
        pass

    return (False, "Unreachable", f"Unreachable ({target_ip})")


# ── 6. Wi-Fi Information ──────────────────────────────────────────────────────

def get_wifi_info() -> WiFiInfo:
    """
    Read Wi-Fi interface details using Windows netsh wlan command.
    Returns WiFiInfo(is_wifi=False) when on Ethernet or Wi-Fi is disconnected.
    """
    try:
        out = _run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=6)

        if not out.strip():
            return WiFiInfo(is_wifi=False, display="Ethernet (No Wi-Fi adapter)")

        # Check connection state
        state_m = re.search(r"State\s*:\s*(\S+)", out)
        if not state_m or state_m.group(1).strip().lower() != "connected":
            return WiFiInfo(is_wifi=False, display="Wi-Fi not connected")

        def _extract(pattern: str) -> str:
            m = re.search(pattern, out, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        ssid       = _extract(r"^\s*SSID\s*:\s*(.+)$")
        bssid      = _extract(r"BSSID\s*:\s*(.+)")
        signal_str = _extract(r"Signal\s*:\s*(\d+)%")
        radio      = _extract(r"Radio type\s*:\s*(.+)")
        channel    = _extract(r"Channel\s*:\s*(\d+)")
        rx_str     = _extract(r"Receive rate \(Mbps\)\s*:\s*([\d\.]+)")
        tx_str     = _extract(r"Transmit rate \(Mbps\)\s*:\s*([\d\.]+)")

        signal_pct       = int(signal_str) if signal_str else -1
        rx_rate          = float(rx_str) if rx_str else -1.0
        tx_rate          = float(tx_str) if tx_str else -1.0

        # Build display string
        parts = []
        if ssid:
            parts.append(f"SSID: {ssid}")
        if signal_pct >= 0:
            parts.append(f"Signal: {signal_pct}%")
        if radio:
            parts.append(radio)
        if channel:
            parts.append(f"Ch:{channel}")

        return WiFiInfo(
            is_wifi=True,
            ssid=ssid,
            bssid=bssid,
            signal_pct=signal_pct,
            radio_type=radio,
            channel=channel,
            receive_rate_mbps=rx_rate,
            transmit_rate_mbps=tx_rate,
            display=" | ".join(parts) if parts else "Wi-Fi Connected",
        )

    except Exception as e:
        return WiFiInfo(is_wifi=False, display=f"Wi-Fi info error: {str(e)}")


# ── 7. Interface Statistics ───────────────────────────────────────────────────

def get_interface_stats(adapter_name: str = None) -> dict:
    """
    Read cumulative bytes sent/received using psutil.
    Useful as a baseline; delta requires two measurements.

    Returns:
        dict with bytes_sent, bytes_recv, packets_sent, packets_recv,
        errin, errout, dropin, dropout.
    """
    try:
        counters = psutil.net_io_counters(pernic=True)
        if adapter_name and adapter_name in counters:
            c = counters[adapter_name]
        else:
            c = psutil.net_io_counters()   # System-wide total

        return {
            "bytes_sent":    c.bytes_sent,
            "bytes_recv":    c.bytes_recv,
            "packets_sent":  c.packets_sent,
            "packets_recv":  c.packets_recv,
            "errin":         c.errin,
            "errout":        c.errout,
            "dropin":        getattr(c, "dropin", 0),
            "dropout":       getattr(c, "dropout", 0),
        }
    except Exception:
        return {}


# ── 8. Legacy diagnose_network (preserved for backward compatibility) ──────────

def diagnose_network(adapter_res, ip_res, gateway_res, dns_res, internet_res):
    """
    Original rule-based diagnostic engine — preserved for backward compatibility.
    New code should use rca_engine.analyze() instead.
    """
    adapter_ok, adapter_name, _ = adapter_res
    ip_ok, ip_addr, _           = ip_res
    gw_has, gw_ip, gw_reachable, _ = gateway_res
    dns_ok, _, _                = dns_res
    internet_ok, _, _           = internet_res

    if not adapter_ok or adapter_name == "None":
        return {"overall_status": "CRITICAL - ADAPTER DISCONNECTED",
                "diagnosis": "Network adapter is disconnected or disabled.",
                "recommendation": "Connect to Wi-Fi or Ethernet and retry.",
                "case_code": "CASE_1"}

    if not ip_ok or ip_addr == "Not Available":
        return {"overall_status": "CRITICAL - NO IP ASSIGNED",
                "diagnosis": "No valid IP address has been assigned.",
                "recommendation": "Reconnect to the network or renew the IP configuration.",
                "case_code": "CASE_2"}

    if not gw_has or not gw_reachable:
        return {"overall_status": "WARNING - GATEWAY UNREACHABLE",
                "diagnosis": "Local network or default gateway connectivity problem.",
                "recommendation": "Check the router, Wi-Fi connection, or local network configuration.",
                "case_code": "CASE_3"}

    if gw_reachable and internet_ok and not dns_ok:
        return {"overall_status": "WARNING - DNS FAILURE",
                "diagnosis": "DNS resolution problem.",
                "recommendation": "Check DNS configuration or try an alternative DNS server.",
                "case_code": "CASE_4"}

    if gw_reachable and dns_ok and not internet_ok:
        return {"overall_status": "WARNING - INTERNET UNREACHABLE",
                "diagnosis": "Internet connectivity problem.",
                "recommendation": "Check router internet access or ISP connectivity.",
                "case_code": "CASE_5"}

    if gw_reachable and dns_ok and internet_ok:
        return {"overall_status": "NORMAL - CONNECTION ONLINE",
                "diagnosis": "Network connection is functioning normally.",
                "recommendation": "No action required.",
                "case_code": "CASE_6"}

    if gw_reachable and not dns_ok and not internet_ok:
        return {"overall_status": "WARNING - NO INTERNET ACCESS",
                "diagnosis": "Gateway reachable but WAN Internet connection is offline.",
                "recommendation": "Check router internet connection or contact your ISP.",
                "case_code": "CASE_HYBRID"}

    return {"overall_status": "WARNING - UNKNOWN NETWORK STATE",
            "diagnosis": "Inconsistent network parameters detected.",
            "recommendation": "Restart your network adapter and retry the diagnostic.",
            "case_code": "CASE_UNKNOWN"}
