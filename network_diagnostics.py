"""
Network Diagnostic Module
Automated Network Diagnostic and Connectivity Analysis Framework

Author: College Academic Project
Target Platform: Windows 10/11
"""

import subprocess
import socket
import re
import psutil


def get_active_adapter():
    """
    Detect available network interfaces using psutil.
    Identify active physical or primary interfaces (Wi-Fi, Ethernet).
    
    Returns:
        (is_connected: bool, adapter_name: str, details: str)
    """
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        active_adapters = []
        priority_keywords = ['wi-fi', 'wifi', 'ethernet', 'local area connection', 'wlan', 'lan']

        for iface_name, iface_stats in stats.items():
            # Check if interface is UP and not a loopback interface
            if iface_stats.isup:
                lower_name = iface_name.lower()
                if 'loopback' in lower_name:
                    continue
                
                # Verify if interface has an assigned non-loopback IPv4 address
                if iface_name in addrs:
                    for addr in addrs[iface_name]:
                        if addr.family == socket.AF_INET:
                            ip = addr.address
                            if not ip.startswith('127.'):
                                active_adapters.append((iface_name, ip))

        if not active_adapters:
            # Fallback: check if any non-loopback interface is UP even if no IP assigned yet
            for iface_name, iface_stats in stats.items():
                if iface_stats.isup and 'loopback' not in iface_name.lower():
                    return (True, iface_name, f"Connected ({iface_name})")
            return (False, "None", "No active network adapter detected")

        # Select the best primary adapter (prefer Wi-Fi or Ethernet)
        best_adapter = active_adapters[0][0]
        for iface_name, _ in active_adapters:
            l_name = iface_name.lower()
            if any(kw in l_name for kw in priority_keywords):
                best_adapter = iface_name
                break

        return (True, best_adapter, best_adapter)

    except Exception as e:
        return (False, "Error", f"Adapter check failed: {str(e)}")


def get_ipv4_address(adapter_name=None):
    """
    Find IPv4 address associated with the active network adapter or system.
    Does not treat loopback (127.0.0.1) or APIPA (169.254.x.x) as valid network IPs.
    
    Returns:
        (has_ip: bool, ip_address: str, details: str)
    """
    try:
        addrs = psutil.net_if_addrs()
        
        # Check specific adapter if provided
        if adapter_name and adapter_name in addrs:
            for addr in addrs[adapter_name]:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if not ip.startswith('127.') and not ip.startswith('169.254.'):
                        return (True, ip, ip)
                    elif ip.startswith('169.254.'):
                        return (False, "Not Available", f"APIPA Self-Assigned IP ({ip})")

        # Fallback search across all adapters
        for iface_name, addr_list in addrs.items():
            if 'loopback' in iface_name.lower():
                continue
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if not ip.startswith('127.') and not ip.startswith('169.254.'):
                        return (True, ip, ip)

        return (False, "Not Available", "No valid IPv4 address assigned")

    except Exception as e:
        return (False, "Not Available", f"IP check error: {str(e)}")


def get_default_gateway():
    """
    Determine system's default gateway using Windows ipconfig command or routing table.
    
    Returns:
        gateway_ip: str or None
    """
    try:
        # Method 1: Parse ipconfig command output
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        output = result.stdout

        # Extract IPv4 Default Gateway entries
        matches = re.findall(r'Default Gateway[ .:]+([\d\.]+)', output)
        valid_gateways = [g for g in matches if g != '0.0.0.0' and not g.startswith('127.')]
        
        if valid_gateways:
            return valid_gateways[0]

        # Method 2: Fallback parsing route print output
        route_res = subprocess.run(
            ["route", "print", "0.0.0.0"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        route_matches = re.findall(r'0\.0\.0\.0\s+0\.0\.0\.0\s+([\d\.]+)', route_res.stdout)
        valid_route_gw = [g for g in route_matches if g != '0.0.0.0' and not g.startswith('127.')]
        if valid_route_gw:
            return valid_route_gw[0]

    except Exception as e:
        print(f"Gateway lookup error: {e}")

    return None


def ping_host(host, timeout_sec=2):
    """
    Test gateway or host reachability using native Windows ping command.
    
    Returns:
        bool: True if host responds, False otherwise.
    """
    if not host or host == "Not Available":
        return False

    try:
        timeout_ms = int(timeout_sec * 1000)
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
        
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec + 2,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )

        out = res.stdout.lower()
        if res.returncode == 0 and ("ttl=" in out or "bytes=" in out or "reply from" in out) and "unreachable" not in out:
            return True
        return False

    except Exception:
        return False


def check_gateway():
    """
    Determine default gateway and test reachability via ping.
    
    Returns:
        (has_gateway: bool, gateway_ip: str, is_reachable: bool, display_str: str)
    """
    gw_ip = get_default_gateway()
    if not gw_ip:
        return (False, "Not Available", False, "Not Available")
    
    reachable = ping_host(gw_ip, timeout_sec=2)
    if reachable:
        return (True, gw_ip, True, gw_ip)
    else:
        return (True, gw_ip, False, f"{gw_ip} (Unreachable)")


def check_dns(domain="google.com"):
    """
    Test DNS resolution using Python socket standard library.
    Attempts to resolve google.com to IPv4.
    
    Returns:
        (is_working: bool, status_str: str, details: str)
    """
    try:
        socket.setdefaulttimeout(3)
        ip = socket.gethostbyname(domain)
        return (True, "Working", f"Resolved {domain} -> {ip}")
    except (socket.gaierror, socket.timeout, Exception):
        return (False, "Failed", f"Failed to resolve {domain}")


def check_internet(target_ip="8.8.8.8"):
    """
    Test internet connectivity independently from DNS by pinging public IP 8.8.8.8.
    
    Returns:
        (is_connected: bool, status_str: str, details: str)
    """
    # Test ping to public IP
    if ping_host(target_ip, timeout_sec=2):
        return (True, "Connected", f"Reachable ({target_ip})")
    
    # Fallback TCP check on port 53 (DNS port on 8.8.8.8)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((target_ip, 53))
        s.close()
        return (True, "Connected", f"TCP Connected ({target_ip}:53)")
    except Exception:
        pass

    return (False, "Unreachable", f"Unreachable ({target_ip})")


def diagnose_network(adapter_res, ip_res, gateway_res, dns_res, internet_res):
    """
    Rule-based diagnostic engine for identifying network connectivity problems.
    
    Evaluates:
    - Adapter status
    - IPv4 status
    - Gateway status & reachability
    - DNS resolution status
    - Direct internet IP reachability
    
    Returns:
        dict containing overall_status, diagnosis, recommendation, and case_code.
    """
    adapter_ok, adapter_name, _ = adapter_res
    ip_ok, ip_addr, _ = ip_res
    gw_has, gw_ip, gw_reachable, _ = gateway_res
    dns_ok, _, _ = dns_res
    internet_ok, _, _ = internet_res

    # CASE 1: Adapter unavailable
    if not adapter_ok or adapter_name == "None":
        return {
            "overall_status": "CRITICAL - ADAPTER DISCONNECTED",
            "diagnosis": "Network adapter is disconnected or disabled.",
            "recommendation": "Connect to Wi-Fi or Ethernet and retry.",
            "case_code": "CASE_1"
        }

    # CASE 2: Adapter available but no valid IP
    if not ip_ok or ip_addr == "Not Available":
        return {
            "overall_status": "CRITICAL - NO IP ASSIGNED",
            "diagnosis": "No valid IP address has been assigned.",
            "recommendation": "Reconnect to the network or renew the IP configuration.",
            "case_code": "CASE_2"
        }

    # CASE 3: IP available but gateway unavailable/unreachable
    if not gw_has or not gw_reachable:
        return {
            "overall_status": "WARNING - GATEWAY UNREACHABLE",
            "diagnosis": "Local network or default gateway connectivity problem.",
            "recommendation": "Check the router, Wi-Fi connection, or local network configuration.",
            "case_code": "CASE_3"
        }

    # CASE 4: Gateway works + internet IP works + DNS fails
    if gw_reachable and internet_ok and not dns_ok:
        return {
            "overall_status": "WARNING - DNS FAILURE",
            "diagnosis": "DNS resolution problem.",
            "recommendation": "Check DNS configuration or try an alternative DNS server.",
            "case_code": "CASE_4"
        }

    # CASE 5: Gateway works + DNS works + internet IP fails
    if gw_reachable and dns_ok and not internet_ok:
        return {
            "overall_status": "WARNING - INTERNET UNREACHABLE",
            "diagnosis": "Internet connectivity problem.",
            "recommendation": "Check router internet access or ISP connectivity.",
            "case_code": "CASE_5"
        }

    # CASE 6: Gateway works + DNS works + internet works
    if gw_reachable and dns_ok and internet_ok:
        return {
            "overall_status": "NORMAL - CONNECTION ONLINE",
            "diagnosis": "Network connection is functioning normally.",
            "recommendation": "No action required.",
            "case_code": "CASE_6"
        }

    # CASE HYBRID: Gateway works + DNS fails + internet IP fails
    if gw_reachable and not dns_ok and not internet_ok:
        return {
            "overall_status": "WARNING - NO INTERNET ACCESS",
            "diagnosis": "Local router gateway is reachable, but WAN Internet connection is offline.",
            "recommendation": "Check router internet connection or contact your Internet Service Provider (ISP).",
            "case_code": "CASE_HYBRID"
        }

    # DEFAULT FALLBACK
    return {
        "overall_status": "WARNING - UNKNOWN NETWORK STATE",
        "diagnosis": "Inconsistent network parameters detected.",
        "recommendation": "Restart your network adapter and retry the diagnostic.",
        "case_code": "CASE_UNKNOWN"
    }
