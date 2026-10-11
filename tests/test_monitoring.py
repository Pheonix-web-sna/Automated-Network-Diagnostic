import threading
import unittest
from unittest.mock import Mock, patch

import main
from test_database import sample_result


class MonitoringTests(unittest.TestCase):
    def test_monitor_scan_runs_collection_compares_history_then_persists(self):
        app = main.IntelliNetApp.__new__(main.IntelliNetApp)
        stop_event = threading.Event()
        app._monitor_stop_event = stop_event
        app._monitor_scan_count = 0
        app._monitor_alert_count = 0
        app.pages = {}
        app.current_page = None
        app._dispatch_ui = Mock()
        result = sample_result()

        def collect_once():
            stop_event.set()
            return result

        order = Mock()
        order.detect.return_value = []
        with patch.object(main.collector, "collect_diagnostic", side_effect=collect_once) as collect, \
             patch.object(main.db, "detect_degradation", side_effect=lambda _result: order.detect()), \
             patch.object(main.db, "save_diagnostic", side_effect=lambda _result: order.save()), \
             patch.object(main.db, "log_event"):
            app._monitoring_loop(interval_sec=0)

        collect.assert_called_once_with()
        self.assertEqual(order.mock_calls, [unittest.mock.call.detect(), unittest.mock.call.save()])
        self.assertEqual(app._monitor_scan_count, 1)
        self.assertGreaterEqual(app._dispatch_ui.call_count, 2)


if __name__ == "__main__":
    unittest.main()
