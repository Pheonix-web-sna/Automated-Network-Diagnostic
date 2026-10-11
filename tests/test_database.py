import tempfile
import unittest
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import config
import db_manager as db
from models import (
    AdapterInfo, DiagnosticResult, DNSInfo, GatewayInfo, HealthScore,
    InternetInfo, IPInfo, PerformanceMetrics, RCAResult, Recommendation, WiFiInfo,
)


def sample_result(*, health=90, latency=25, loss=0, ping_count=4, dns=True):
    return DiagnosticResult(
        timestamp=datetime(2026, 10, 11, 9, 30),
        adapter=AdapterInfo(True, "Wi-Fi", "Connected", "Wi-Fi"),
        ip=IPInfo(True, "192.0.2.10", "255.255.255.0"),
        gateway=GatewayInfo(True, "192.0.2.1", True),
        wifi=WiFiInfo(True, "Test network", 75),
        dns=DNSInfo(dns, "example.com", "192.0.2.53" if dns else ""),
        internet=InternetInfo(True, "203.0.113.1", "TCP"),
        performance=PerformanceMetrics(
            latency, latency, latency, 0 if latency >= 0 else -1,
            loss, ping_count, "203.0.113.1",
            "ICMP unavailable" if latency < 0 else "",
        ),
        health=HealthScore(health),
        rca=RCAResult("CASE_6", "Healthy", [], 99, "NORMAL", "NORMAL"),
        recommendation=Recommendation("NORMAL", "No action required", [], "CASE_6"),
    )


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        directory = Path(self.temp_dir.name)
        self.patches = [
            patch.object(db, "DB_DIR", str(directory)),
            patch.object(db, "DB_PATH", str(directory / "test.db")),
            patch.object(db, "LEGACY_DB_PATH", str(directory / "legacy.db")),
        ]
        for item in self.patches:
            item.start()
        db.init_db()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_session_history_round_trip_and_unmeasured_loss_stays_null(self):
        db.save_diagnostic(sample_result(latency=-1, loss=-1, ping_count=0))

        session = db.get_recent_sessions(1)[0]
        loss_row = db.get_packet_loss_history(1)[0]
        self.assertIsNone(session["packet_loss_pct"])
        self.assertIsNone(loss_row["loss_pct"])
        self.assertEqual(db.get_session_count(), 1)
        self.assertEqual(len(db.get_health_history(1)), 1)

    def test_history_retention_limit_is_enforced(self):
        with patch.object(config, "MAX_HISTORY_SESSIONS", 2):
            for score in (90, 80, 70):
                db.save_diagnostic(sample_result(health=score))

            sessions = db.get_recent_sessions(10)
            self.assertEqual(len(sessions), 2)
            self.assertEqual([row["health_score"] for row in sessions], [70, 80])

    def test_degradation_uses_prior_history_before_current_scan_is_saved(self):
        for _ in range(3):
            db.save_diagnostic(sample_result(health=95))

        alerts = db.detect_degradation(sample_result(health=60))

        self.assertTrue(any("Health score dropped" in item for item in alerts))
        self.assertEqual(db.get_session_count(), 3)

    def test_event_log_retention_is_bounded(self):
        with patch.object(config, "MAX_EVENT_LOG_ENTRIES", 3):
            for index in range(5):
                db.log_event("TEST", f"event {index}")

            events = db.get_event_log(10)
            self.assertEqual(db.get_event_count(), 3)
            self.assertEqual([event["message"] for event in events], ["event 4", "event 3", "event 2"])

    def test_legacy_database_migration_preserves_committed_wal_data(self):
        migration_dir = Path(self.temp_dir.name) / "migration"
        migration_dir.mkdir()
        legacy_path = migration_dir / "legacy.db"
        destination_path = migration_dir / "current.db"
        legacy = sqlite3.connect(legacy_path)
        try:
            legacy.execute("PRAGMA journal_mode=WAL")
            legacy.execute("CREATE TABLE migration_probe (value TEXT)")
            legacy.execute("INSERT INTO migration_probe VALUES ('preserved')")
            legacy.commit()

            with patch.object(db, "DB_DIR", str(migration_dir)), \
                 patch.object(db, "DB_PATH", str(destination_path)), \
                 patch.object(db, "LEGACY_DB_PATH", str(legacy_path)):
                db.init_db()
                connection = sqlite3.connect(destination_path)
                try:
                    copied = connection.execute("SELECT value FROM migration_probe").fetchone()
                finally:
                    connection.close()
        finally:
            legacy.close()

        self.assertEqual(copied[0], "preserved")


if __name__ == "__main__":
    unittest.main()
