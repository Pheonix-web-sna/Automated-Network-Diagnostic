import subprocess
import unittest
from unittest.mock import Mock

from remediation import execute_remediation


class RemediationTests(unittest.TestCase):
    def test_flush_dns_requires_confirmation(self):
        runner = Mock()
        result = execute_remediation("flush_dns", command_runner=runner)

        self.assertEqual(result.status, "cancelled")
        runner.assert_not_called()

    def test_renew_ip_requires_confirmation(self):
        runner = Mock()
        result = execute_remediation("renew_ip", command_runner=runner)

        self.assertEqual(result.status, "cancelled")
        runner.assert_not_called()

    def test_confirmed_flush_dns_runs_only_allow_listed_command(self):
        runner = Mock(return_value=subprocess.CompletedProcess(
            ["ipconfig", "/flushdns"], 0, "Successfully flushed the DNS Resolver Cache.", ""
        ))
        result = execute_remediation("flush_dns", confirmed=True, command_runner=runner)

        self.assertTrue(result.succeeded)
        self.assertIn("Successfully flushed", result.message)
        args, kwargs = runner.call_args
        self.assertEqual(args[0], ["ipconfig", "/flushdns"])
        self.assertFalse(kwargs["shell"])

    def test_confirmed_renew_ip_runs_renew_only(self):
        runner = Mock(return_value=subprocess.CompletedProcess(
            ["ipconfig", "/renew"], 0, "Renewed address.", ""
        ))
        result = execute_remediation("renew_ip", confirmed=True, command_runner=runner)

        self.assertTrue(result.succeeded)
        self.assertEqual(runner.call_args.args[0], ["ipconfig", "/renew"])

    def test_command_failure_is_reported(self):
        runner = Mock(return_value=subprocess.CompletedProcess(
            ["ipconfig", "/flushdns"], 1, "", "Access is denied."
        ))
        result = execute_remediation("flush_dns", confirmed=True, command_runner=runner)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.message, "Access is denied.")

    def test_command_exception_is_reported(self):
        runner = Mock(side_effect=OSError("command unavailable"))
        result = execute_remediation("renew_ip", confirmed=True, command_runner=runner)

        self.assertEqual(result.status, "failed")
        self.assertIn("command unavailable", result.message)

    def test_rerun_diagnostics_calls_callback_without_network_command(self):
        callback = Mock(return_value=True)
        runner = Mock()
        result = execute_remediation(
            "rerun_diagnostics",
            diagnostic_callback=callback,
            command_runner=runner,
        )

        self.assertTrue(result.succeeded)
        callback.assert_called_once_with()
        runner.assert_not_called()

    def test_rerun_diagnostics_reports_already_running(self):
        result = execute_remediation(
            "rerun_diagnostics",
            diagnostic_callback=lambda: False,
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("already running", result.message)

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            execute_remediation("change_dns_server", confirmed=True)


if __name__ == "__main__":
    unittest.main()
