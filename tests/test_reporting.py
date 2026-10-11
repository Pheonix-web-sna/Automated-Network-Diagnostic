import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from models import (
    AdapterInfo,
    DiagnosticResult,
    DNSInfo,
    GatewayInfo,
    HealthScore,
    InternetInfo,
    IPInfo,
    PerformanceMetrics,
    RCAResult,
    Recommendation,
    WiFiInfo,
)
from reporting import build_report_sections, generate_pdf_report
from remediation import ActionRecord


def sample_result():
    return DiagnosticResult(
        timestamp=datetime(2026, 10, 11, 9, 30, 0),
        adapter=AdapterInfo(
            is_up=True,
            name="Wi-Fi",
            display="Connected",
            adapter_type="Wi-Fi",
            speed_mbps=866,
            mac_address="00-11-22-33-44-55",
        ),
        ip=IPInfo(is_valid=True, ipv4="192.168.1.20", subnet_mask="255.255.255.0"),
        gateway=GatewayInfo(
            has_gateway=True,
            ip="192.168.1.1",
            is_reachable=True,
        ),
        wifi=WiFiInfo(
            is_wifi=True,
            ssid="Office Wi-Fi",
            signal_pct=92,
            radio_type="802.11ax",
        ),
        dns=DNSInfo(
            is_working=True,
            domain_tested="google.com",
            resolved_ip="142.250.72.14",
            display="Resolved successfully",
            dns_servers=["192.168.1.1", "1.1.1.1"],
        ),
        internet=InternetInfo(
            is_connected=True,
            target_ip="8.8.8.8",
            method="ICMP",
            display="Reply received",
        ),
        performance=PerformanceMetrics(
            avg_latency_ms=24.5,
            min_latency_ms=19.0,
            max_latency_ms=34.0,
            jitter_ms=6.0,
            packet_loss_pct=0.0,
            ping_count=4,
            target_host="8.8.8.8",
        ),
        health=HealthScore(score=96),
        rca=RCAResult(
            case_code="CASE_6",
            primary_cause="Network connection is functioning normally.",
            secondary_causes=[],
            confidence=97,
            overall_status="NORMAL",
            severity="NORMAL",
        ),
        recommendation=Recommendation(
            severity="NORMAL",
            summary="All connectivity checks passed.",
            steps=["No action required."],
            case_code="CASE_6",
        ),
    )


class DiagnosticReportTests(unittest.TestCase):
    def test_report_sections_cover_requested_content_and_actions(self):
        action = ActionRecord(
            action="Flush DNS cache",
            status="Completed",
            details="DNS cache was flushed.",
            timestamp=datetime(2026, 10, 11, 9, 35, 0),
        )

        sections = build_report_sections(sample_result(), [action])
        section_names = [name for name, _ in sections]
        self.assertEqual(
            section_names,
            [
                "Network Configuration",
                "Connectivity Results",
                "Performance Analysis",
                "Root-Cause Analysis",
                "Diagnostic Confidence",
                "Recommendations",
                "Actions Performed",
            ],
        )

        network_rows = dict(sections[0][1])
        self.assertEqual(network_rows["Configured DNS servers"], "192.168.1.1, 1.1.1.1")
        action_rows = sections[-1][1]
        self.assertIn("Flush DNS cache", action_rows[0][0])
        self.assertIn("DNS cache was flushed.", action_rows[0][1])

    def test_pdf_is_written_and_has_pdf_signature(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp_dir:
            destination = Path(temp_dir) / "diagnostic-report.pdf"
            result_path = generate_pdf_report(sample_result(), destination)

            self.assertEqual(result_path, destination)
            self.assertTrue(destination.is_file())
            content = destination.read_bytes()
            self.assertTrue(content.startswith(b"%PDF-"))
            self.assertGreater(len(content), 2_000)

    def test_empty_action_history_is_explicit(self):
        actions = dict(build_report_sections(sample_result())[-1][1])
        self.assertIn("No actions performed", actions)


if __name__ == "__main__":
    unittest.main()
