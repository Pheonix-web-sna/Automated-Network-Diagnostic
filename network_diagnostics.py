"""
network_diagnostics.py — IntelliNet Network Probe Layer
Windows-oriented network probes with bounded subprocess and socket calls.
Adapter-scoped lookups avoid mixing IP, gateway, and traffic data across interfaces.
"""

import subprocess
import socket
import re
import json
import psutil
import sys
import os

# Allow running standalone or as part of the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models import WiFiInfo
import config as cfg


# ── Subprocess helper ────────────────────────────────────────────────────────

def _run_cmd(cmd: list, timeout: int = cfg.NETWORK_COMMAND_TIMEOUT_SEC) -> str:
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
                        if not ip.startswith(("127.", "169.254.")):
                            active_adapters.append((iface_name, ip))

        if not active_adapters:
            # Fallback: interface UP but no IP yet
            for iface_name, iface_stats in stats.items():
                if iface_stats.isup and "loopback" not in iface_name.lower():
                    return (True, iface_name, f"Connected ({iface_name})")
            return (False, "None", "No active network adapter detected")

        # Prefer the interface used by the active default route. This avoids
        # pairing a Wi-Fi address with an Ethernet/VPN gateway on multi-adapter PCs.
        route_ip = _get_default_route_interface_ip()
        if route_ip:
            for iface_name, ip in active_adapters:
                if ip == route_ip:
                    return (True, iface_name, iface_name)

        # Fall back to a familiar physical adapter when route output is unavailable.
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

        if adapter_name:
            # Never borrow an address from another interface. That can report a
            # VPN/Ethernet lease as the Wi-Fi adapter's address when the latter
            # is disconnected or still has only an APIPA address.
            for addr in addrs.get(adapter_name, []):
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if not ip.startswith("127.") and not ip.startswith("169.254."):
                        return (True, ip, ip)
                    elif ip.startswith("169.254."):
                        return (False, "Not Available", f"APIPA Self-Assigned IP ({ip})")
            return (False, "Not Available", "No valid IPv4 address assigned to the selected adapter")

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

def _get_default_route_rows(output: str):
    """Parse numeric gateway/interface pairs from Windows route output."""
    return re.findall(
        r"0\.0\.0\.0\s+0\.0\.0\.0\s+([\d.]+)\s+([\d.]+)",
        output,
    )


def _get_default_route_interface_ip():
    try:
        output = _run_cmd(["route", "print", "0.0.0.0"])
        for gateway, interface_ip in _get_default_route_rows(output):
            if gateway != "0.0.0.0" and not gateway.startswith("127."):
                return interface_ip
    except Exception:
        return None
    return None


def get_default_gateway(adapter_name=None):
    """
    Determine default gateway.

    Method 1 (primary): route print 0.0.0.0 — language-independent numeric output.
    Method 2 (fallback): ipconfig — works on English Windows.

    Returns:
        gateway_ip: str or None
    """
    try:
        # PRIMARY: route print — language-independent
        out = _run_cmd(["route", "print", "0.0.0.0"])
        rows = _get_default_route_rows(out)
        valid = [
            (gateway, interface_ip)
            for gateway, interface_ip in rows
            if gateway != "0.0.0.0" and not gateway.startswith("127.")
        ]
        if adapter_name:
            addrs = psutil.net_if_addrs().get(adapter_name, [])
            adapter_ips = {
                addr.address for addr in addrs
                if addr.family == socket.AF_INET and not addr.address.startswith(("127.", "169.254."))
            }
            matching = [gateway for gateway, interface_ip in valid if interface_ip in adapter_ips]
            return matching[0] if matching else None
        if valid:
            return valid[0][0]

        # FALLBACK: ipconfig (English Windows only)
        if adapter_name:
            return None
        out2 = _run_cmd(["ipconfig"])
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
        timeout=cfg.DNS_SERVER_QUERY_TIMEOUT_SEC,
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


def ping_host(host: str, timeout_sec: int = cfg.QUICK_PING_TIMEOUT) -> bool:
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
                       timeout=timeout_sec + cfg.PING_QUICK_TIMEOUT_BUFFER_SEC)
        out_lower = out.lower()
        return (
            "ttl=" in out_lower or
            "bytes=" in out_lower or
            "reply from" in out_lower
        ) and "unreachable" not in out_lower and "100% loss" not in out_lower
    except Exception:
        return False


def check_gateway(adapter_name=None):
    """
    Detect gateway and test reachability via ping.

    Returns:
        (has_gateway: bool, gateway_ip: str, is_reachable: bool, display_str: str)
    """
    gw = get_default_gateway(adapter_name)
    if not gw:
        return (False, "Not Available", False, "Not Available")
    reachable = ping_host(gw, timeout_sec=cfg.QUICK_PING_TIMEOUT)
    if reachable:
        return (True, gw, True, gw)
    else:
        return (True, gw, False, f"{gw} (Unreachable)")


# ── 4. DNS Resolution ────────────────────────────────────────────────────────

def check_dns(domain: str = cfg.DNS_TEST_DOMAIN):
    """
    Test DNS resolution with a bounded timeout on Windows.

    Returns:
        (is_working: bool, status_str: str, details: str)
    """
    if sys.platform == "win32":
        # getaddrinfo has no per-call timeout. Use the Windows DNS client in a
        # child process so a stuck resolver can be terminated without freezing
        # the diagnostic or monitoring worker indefinitely.
        safe_domain = str(domain).replace("'", "''")
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"$addresses = Resolve-DnsName -Name '{safe_domain}' -Type A -DnsOnly "
            "-ErrorAction Stop | Where-Object { $_.IPAddress } "
            "| Select-Object -ExpandProperty IPAddress; "
            "if (-not $addresses) { exit 1 }; "
            "ConvertTo-Json -InputObject @($addresses) -Compress"
        )
        try:
            flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                timeout=cfg.DNS_SOCKET_TIMEOUT_SEC,
                creationflags=flags,
                check=False,
            )
            if result.returncode != 0:
                detail = (result.stderr or "DNS query returned no addresses").strip()
                return (False, "Failed", f"Failed to resolve {domain}: {detail}")
            addresses = json.loads(result.stdout or "[]")
            if isinstance(addresses, str):
                addresses = [addresses]
            if addresses:
                return (True, "Working", f"Resolved {domain} -> {addresses[0]}")
            return (False, "Failed", f"No result for {domain}")
        except subprocess.TimeoutExpired:
            return (False, "Failed", f"DNS lookup timed out after {cfg.DNS_SOCKET_TIMEOUT_SEC}s ({domain})")
        except FileNotFoundError:
            return (False, "Failed", "PowerShell DNS query utility was not found")
        except (TypeError, ValueError) as exc:
            return (False, "Failed", f"Invalid DNS query response: {exc}")
        except Exception as exc:
            return (False, "Failed", f"DNS query error: {exc}")

    # Non-Windows fallback for the diagnostic module's unit tests and CLI use.
    # Windows is the supported desktop platform and uses the bounded process above.
    try:
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
        with socket.create_connection(
            (cfg.TCP_FALLBACK_HOST, cfg.TCP_FALLBACK_PORT),
            timeout=cfg.TCP_FALLBACK_TIMEOUT_SEC,
        ):
            pass
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
        out = _run_cmd(["netsh", "wlan", "show", "interfaces"])

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
        if adapter_name:
            c = counters.get(adapter_name)
            if c is None:
                return {}
        else:
            c = psutil.net_io_counters()   # System-wide total only when no adapter was selected

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
