import socket
import subprocess
import unittest
from unittest.mock import MagicMock, Mock
from types import SimpleNamespace
from unittest.mock import patch

import network_diagnostics as nd
import performance
import rca_engine
import collector
from models import (
    AdapterInfo, DiagnosticResult, DNSInfo, GatewayInfo, HealthScore,
    InternetInfo, IPInfo, PerformanceMetrics, RCAResult, Recommendation, WiFiInfo,
)
from datetime import datetime


def diagnostic_result(*, adapter=True, ip=True, gateway=True, dns=True,
                      internet=True, latency=24, loss=0, ping_count=4):
    return DiagnosticResult(
        timestamp=datetime(2026, 10, 11),
        adapter=AdapterInfo(adapter, "Wi-Fi", "Connected", "Wi-Fi"),
        ip=IPInfo(ip, "192.0.2.10" if ip else "Not Available"),
        gateway=GatewayInfo(gateway, "192.0.2.1", gateway),
        wifi=WiFiInfo(True, ssid="Test network", signal_pct=70),
        dns=DNSInfo(dns, "example.com"),
        internet=InternetInfo(internet, "203.0.113.1", "TCP"),
        performance=PerformanceMetrics(
            avg_latency_ms=latency,
            min_latency_ms=latency if latency >= 0 else -1,
            max_latency_ms=latency if latency >= 0 else -1,
            jitter_ms=0 if latency >= 0 else -1,
            packet_loss_pct=loss,
            ping_count=ping_count,
            target_host="203.0.113.1",
        ),
        health=HealthScore(90),
        rca=RCAResult("", "", [], 0, "", ""),
        recommendation=Recommendation("", "", [], ""),
    )


class AdapterSelectionTests(unittest.TestCase):
    @patch.object(nd.psutil, "net_if_addrs")
    def test_ip_is_never_borrowed_from_a_different_adapter(self, get_addrs):
        get_addrs.return_value = {
            "Wi-Fi": [SimpleNamespace(family=socket.AF_INET, address="169.254.1.2")],
            "Ethernet": [SimpleNamespace(family=socket.AF_INET, address="192.168.1.9")],
        }

        result = nd.get_ipv4_address("Wi-Fi")

        self.assertFalse(result[0])
        self.assertEqual(result[1], "Not Available")
        self.assertIn("APIPA", result[2])


class DNSProbeTests(unittest.TestCase):
    @patch("network_diagnostics.sys.platform", "win32")
    @patch("network_diagnostics.subprocess.run")
    def test_dns_resolution_uses_timeout_and_returns_resolved_address(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '"192.0.2.8"', "")

        result = nd.check_dns("example.com")

        self.assertTrue(result[0])
        self.assertIn("192.0.2.8", result[2])
        self.assertEqual(run.call_args.kwargs["timeout"], nd.cfg.DNS_SOCKET_TIMEOUT_SEC)

    @patch("network_diagnostics.sys.platform", "win32")
    @patch("network_diagnostics.subprocess.run", side_effect=subprocess.TimeoutExpired("powershell", 3))
    def test_dns_timeout_is_reported_as_failure(self, _run):
        result = nd.check_dns("example.com")
        self.assertFalse(result[0])
        self.assertIn("timed out", result[2])

    @patch("network_diagnostics.sys.platform", "win32")
    @patch("network_diagnostics.subprocess.run")
    def test_dns_server_failure_is_reported_without_throwing(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "DNS query failed")
        result = nd.check_dns("example.com")
        self.assertFalse(result[0])
        self.assertIn("DNS query failed", result[2])


class InternetProbeTests(unittest.TestCase):
    @patch("network_diagnostics.socket.create_connection", side_effect=OSError("network down"))
    @patch("network_diagnostics.ping_host", return_value=False)
    def test_no_internet_is_reported_when_all_reachability_probes_fail(self, ping, _connect):
        result = nd.check_internet("203.0.113.1")
        self.assertFalse(result[0])
        self.assertEqual(ping.call_count, 2)

    @patch("network_diagnostics.socket.create_connection", return_value=MagicMock())
    @patch("network_diagnostics.ping_host", return_value=False)
    def test_tcp_fallback_can_confirm_internet_when_icmp_is_blocked(self, _ping, connect):
        result = nd.check_internet("203.0.113.1")
        self.assertTrue(result[0])
        self.assertIn("TCP connected", result[2])


class PingParsingTests(unittest.TestCase):
    def test_completed_ping_with_no_replies_is_100_percent_loss_not_missing_data(self):
        output = "Packets: Sent = 4, Received = 0, Lost = 4 (100% loss)"
        metrics = performance._parse_ping_output(output, 4, "203.0.113.1")

        self.assertFalse(metrics.is_valid)
        self.assertTrue(metrics.has_packet_measurement)
        self.assertEqual(metrics.packet_loss_pct, 100)
        self.assertEqual(metrics.ping_count, 4)

    def test_latency_and_partial_packet_loss_are_counted_separately(self):
        output = (
            "Reply from 203.0.113.1: bytes=32 time=250ms TTL=50\n"
            "Reply from 203.0.113.1: bytes=32 time=260ms TTL=50\n"
            "Packets: Sent = 4, Received = 2, Lost = 2 (50% loss)\n"
            "Minimum = 250ms, Maximum = 260ms, Average = 255ms"
        )
        metrics = performance._parse_ping_output(output, 4, "203.0.113.1")

        self.assertEqual(metrics.avg_latency_ms, 255)
        self.assertEqual(metrics.packet_loss_pct, 50)
        self.assertEqual(metrics.ping_count, 4)


class RootCauseScenarioTests(unittest.TestCase):
    def test_normal_wifi_is_healthy(self):
        self.assertEqual(rca_engine.analyze(diagnostic_result()).case_code, "CASE_6")

    def test_disconnected_wifi_is_adapter_failure(self):
        self.assertEqual(rca_engine.analyze(diagnostic_result(adapter=False, ip=False, gateway=False)).case_code, "CASE_1")

    def test_working_dns_but_no_internet_is_wan_case(self):
        self.assertEqual(rca_engine.analyze(diagnostic_result(internet=False)).case_code, "CASE_5")

    def test_dns_failure_with_internet_access_is_dns_case(self):
        self.assertEqual(rca_engine.analyze(diagnostic_result(dns=False)).case_code, "CASE_4")

    def test_high_latency_and_packet_loss_are_performance_case(self):
        result = diagnostic_result(latency=250, loss=25)
        analysis = rca_engine.analyze(result)
        self.assertEqual(analysis.case_code, "CASE_PERF")
        self.assertTrue(any("latency" in cause.lower() for cause in analysis.secondary_causes))
        self.assertTrue(any("packet loss" in cause.lower() for cause in analysis.secondary_causes))

    def test_loss_only_measurement_does_not_invent_latency(self):
        result = diagnostic_result(latency=-1, loss=100)
        analysis = rca_engine.analyze(result)
        self.assertEqual(analysis.case_code, "CASE_PERF")
        self.assertTrue(any("filter ICMP" in cause for cause in analysis.secondary_causes))


class CollectorIntegrationTests(unittest.TestCase):
    def test_reachability_fallback_target_is_preserved(self):
        self.assertEqual(
            collector._internet_probe_target("ICMP reachable (1.1.1.1)"),
            ("1.1.1.1", "ICMP"),
        )
        self.assertEqual(
            collector._internet_probe_target("TCP connected (8.8.8.8:53)"),
            ("8.8.8.8", "TCP"),
        )

    def test_shared_collector_assembles_wifi_result_and_reports_progress(self):
        wifi = WiFiInfo(True, ssid="Test network", signal_pct=80)
        metrics = PerformanceMetrics(12, 10, 14, 4, 0, 4, "8.8.8.8")
        progress = []
        with patch.object(collector.nd, "get_active_adapter", return_value=(True, "Wi-Fi", "Wi-Fi")), \
             patch.object(collector.nd, "get_ipv4_address", return_value=(True, "192.0.2.10", "192.0.2.10")), \
             patch.object(collector.nd, "check_gateway", return_value=(True, "192.0.2.1", True, "192.0.2.1")), \
             patch.object(collector.nd, "get_wifi_info", return_value=wifi), \
             patch.object(collector.nd, "check_dns", return_value=(True, "Working", "Resolved example.com -> 192.0.2.53")), \
             patch.object(collector.nd, "check_internet", return_value=(True, "Connected", "TCP connected (8.8.8.8:53)")), \
             patch.object(collector.nd, "get_dns_servers", return_value=["192.0.2.53"]), \
             patch.object(collector.nd, "get_interface_stats", return_value={}), \
             patch.object(collector.perf, "measure_performance", return_value=metrics):
            result = collector.collect_diagnostic(lambda *event: progress.append(event))

        self.assertEqual(result.rca.case_code, "CASE_6")
        self.assertEqual(result.dns.resolved_ip, "192.0.2.53")
        self.assertEqual(result.internet.method, "TCP")
        self.assertEqual(result.internet.target_ip, "8.8.8.8")
        self.assertEqual([event[0] for event in progress], list(range(8)) + [None])
        self.assertEqual(progress[-1][7], 100)


if __name__ == "__main__":
    unittest.main()
