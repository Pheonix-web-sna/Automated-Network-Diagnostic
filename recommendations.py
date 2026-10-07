"""
recommendations.py - IntelliNet Recommendation Engine

Maps RCAResult case codes to structured, step-by-step fix instructions.
Each recommendation has:
  - severity: "CRITICAL", "WARNING", "PERFORMANCE", "NORMAL"
  - summary:  One-sentence summary of the issue
  - steps:    Numbered actionable instructions for the user
  - case_code: Reference to which diagnostic case triggered this
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import RCAResult, Recommendation


# ── Recommendation registry ───────────────────────────────────────────────────
# Maps case_code -> Recommendation factory function

def _make(severity, summary, steps, case_code) -> Recommendation:
    return Recommendation(
        severity=severity,
        summary=summary,
        steps=steps,
        case_code=case_code,
    )


_RECOMMENDATIONS = {

    "CASE_1": lambda rca: _make(
        severity="CRITICAL",
        summary="Network adapter is disconnected or disabled. No network access is possible.",
        steps=[
            "Check that your Wi-Fi is turned on (look for the Wi-Fi icon in the Windows taskbar).",
            "If using Ethernet, verify the cable is firmly connected to both the laptop and the router.",
            "Open Settings -> Network & Internet -> Wi-Fi and toggle Wi-Fi OFF then ON.",
            "Open Device Manager -> Network Adapters and check for a yellow warning icon.",
            "Right-click the adapter and select 'Enable Device' if it is disabled.",
            "Restart your computer if the issue persists after enabling the adapter.",
        ],
        case_code="CASE_1",
    ),

    "CASE_2": lambda rca: _make(
        severity="CRITICAL",
        summary="Adapter is active but no valid IP address was assigned (DHCP failure or network misconfiguration).",
        steps=[
            "Right-click the Wi-Fi / Ethernet icon in the taskbar and select 'Troubleshoot problems'.",
            "Open Command Prompt (cmd) as Administrator and run:\n   ipconfig /release\n   ipconfig /renew",
            "If using Wi-Fi: Disconnect from the network and reconnect.",
            "Forget the Wi-Fi network (Settings -> Network & Internet -> Wi-Fi -> Manage known networks) and rejoin.",
            "Restart your router by unplugging it for 30 seconds, then plug it back in.",
            "If the issue continues, check that your router's DHCP server is enabled (log in to router admin panel).",
        ],
        case_code="CASE_2",
    ),

    "CASE_3": lambda rca: _make(
        severity="WARNING",
        summary="IP address is assigned but the default gateway (router) is unreachable.",
        steps=[
            "Check that your router is powered on and all indicator lights are normal.",
            "If using Ethernet: check that the cable is not damaged and is plugged in at both ends.",
            "If using Wi-Fi: move closer to the router to improve signal strength.",
            "Restart your router by unplugging it for 30 seconds.",
            "Try to ping your gateway manually: open Command Prompt and type:\n   ping <gateway_ip>",
            "Check your router admin panel to ensure it is functioning normally.",
            "If you are in a corporate network, contact your network administrator.",
        ],
        case_code="CASE_3",
    ),

    "CASE_4": lambda rca: _make(
        severity="WARNING",
        summary="DNS resolution is failing. Internet routing works, but domain names cannot be resolved.",
        steps=[
            "Open Command Prompt and flush the DNS cache:\n   ipconfig /flushdns",
            "Try changing your DNS server to Google DNS:\n   Preferred: 8.8.8.8\n   Alternate:  8.8.4.4",
            "To change DNS: Settings -> Network & Internet -> [adapter] -> DNS server assignment -> Manual.",
            "Alternatively, try Cloudflare DNS:\n   Preferred: 1.1.1.1\n   Alternate:  1.0.0.1",
            "Restart your DNS client service:\n   Open Services -> DNS Client -> Restart.",
            "If on a corporate network, check that the company DNS server address is correctly configured.",
            "Disable any VPN or proxy software temporarily and retry the diagnostic.",
        ],
        case_code="CASE_4",
    ),

    "CASE_5": lambda rca: _make(
        severity="WARNING",
        summary="Gateway and DNS work, but internet connectivity to public IPs is unreachable.",
        steps=[
            "Check whether your router's WAN (internet) light is on and stable.",
            "Log in to your router admin panel and check the WAN/Internet connection status.",
            "Restart the router and modem (if separate): unplug both for 60 seconds.",
            "Contact your ISP to check for outages in your area.",
            "Temporarily disable Windows Firewall and retry: \n   Settings -> Windows Security -> Firewall & network protection -> Turn off.",
            "Check if a VPN is active - disable it and test again.",
            "Ask your ISP if your PPPoE/DHCP lease from the ISP side has expired or changed.",
        ],
        case_code="CASE_5",
    ),

    "CASE_HYBRID": lambda rca: _make(
        severity="WARNING",
        summary="Local router is reachable but all WAN internet access is completely unavailable.",
        steps=[
            "This is almost certainly a WAN-side outage (between your router and the internet).",
            "Check the router's WAN / Internet status light - it may be off or amber.",
            "Log in to the router admin panel and verify the WAN connection status.",
            "Restart your modem (the device connected to the phone line / coaxial / fiber).",
            "Contact your ISP and report the outage - check their service status page.",
            "If using PPPoE: verify your ISP username and password in the router settings.",
        ],
        case_code="CASE_HYBRID",
    ),

    "CASE_PERF": lambda rca: _make(
        severity="PERFORMANCE",
        summary="All connectivity layers are functional, but network performance is degraded (high latency or packet loss).",
        steps=[
            "Move closer to your Wi-Fi router to improve signal strength.",
            "Switch from 2.4 GHz to 5 GHz Wi-Fi band if your router supports it.",
            "Reduce the number of devices connected to the network.",
            "Restart your router to clear any congestion or memory leaks.",
            "Run a speed test at speedtest.net to confirm actual throughput.",
            "Check for large background downloads or streaming consuming bandwidth.",
            "If using Ethernet and still experiencing loss, try a different cable.",
            "Contact your ISP if high latency or packet loss persists across different times of day.",
        ],
        case_code="CASE_PERF",
    ),

    "CASE_6": lambda rca: _make(
        severity="NORMAL",
        summary="Network connection is fully operational. All diagnostic checks passed.",
        steps=[
            "No action required - your network connection is working correctly.",
            "All connectivity layers (adapter, IP, gateway, DNS, internet) are functioning.",
            "Run the diagnostic again after any configuration changes to verify continued health.",
        ],
        case_code="CASE_6",
    ),

    "CASE_UNKNOWN": lambda rca: _make(
        severity="WARNING",
        summary="Network state could not be determined. Indeterminate diagnostic result.",
        steps=[
            "Run the diagnostic again to check for consistent results.",
            "Restart your network adapter:\n   Settings -> Network & Internet -> [adapter] -> Disable -> Enable.",
            "Check for conflicting network adapters in Device Manager.",
            "Run Windows built-in network troubleshooter:\n   Settings -> System -> Troubleshoot -> Other troubleshooters -> Internet Connections.",
        ],
        case_code="CASE_UNKNOWN",
    ),
}


def get_recommendation(rca: RCAResult) -> Recommendation:
    """
    Look up and return the Recommendation for a given RCAResult.

    Falls back gracefully to CASE_UNKNOWN if the case_code is not in the registry.
    """
    factory = _RECOMMENDATIONS.get(rca.case_code) or _RECOMMENDATIONS["CASE_UNKNOWN"]
    return factory(rca)
