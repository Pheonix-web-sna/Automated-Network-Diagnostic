import unittest
from unittest.mock import patch

import network_diagnostics
import socket
from types import SimpleNamespace


class DNSConfigurationTests(unittest.TestCase):
    @patch("network_diagnostics._run_cmd", return_value='["192.168.1.1","1.1.1.1"]')
    @patch("network_diagnostics.sys.platform", "win32")
    def test_dns_servers_are_parsed_for_selected_adapter(self, run_cmd):
        servers = network_diagnostics.get_dns_servers("Wi-Fi")

        self.assertEqual(servers, ["192.168.1.1", "1.1.1.1"])
        command = run_cmd.call_args.args[0]
        self.assertEqual(command[0:3], ["powershell", "-NoProfile", "-NonInteractive"])
        self.assertIn("InterfaceAlias -eq 'Wi-Fi'", command[-1])

    @patch("network_diagnostics._run_cmd", return_value="null")
    @patch("network_diagnostics.sys.platform", "win32")
    def test_empty_dns_configuration_returns_empty_list(self, _run_cmd):
        self.assertEqual(network_diagnostics.get_dns_servers("Wi-Fi"), [])

    @patch("network_diagnostics._run_cmd")
    @patch("network_diagnostics.sys.platform", "linux")
    def test_non_windows_platform_does_not_run_powershell(self, run_cmd):
        self.assertEqual(network_diagnostics.get_dns_servers("wlan0"), [])
        run_cmd.assert_not_called()


class GatewayAdapterTests(unittest.TestCase):
    @patch("network_diagnostics.psutil.net_if_addrs")
    @patch("network_diagnostics._run_cmd")
    def test_gateway_is_selected_for_the_requested_adapter(self, run_cmd, get_addrs):
        run_cmd.return_value = (
            "0.0.0.0 0.0.0.0 192.0.2.1 192.0.2.10 25\n"
            "0.0.0.0 0.0.0.0 198.51.100.1 198.51.100.10 35\n"
        )
        get_addrs.return_value = {
            "Wi-Fi": [SimpleNamespace(family=socket.AF_INET, address="198.51.100.10")]
        }

        gateway = network_diagnostics.get_default_gateway("Wi-Fi")

        self.assertEqual(gateway, "198.51.100.1")

    @patch("network_diagnostics.psutil.net_if_addrs")
    @patch("network_diagnostics._run_cmd")
    def test_gateway_does_not_fall_back_to_another_adapter(self, run_cmd, get_addrs):
        run_cmd.return_value = "0.0.0.0 0.0.0.0 192.0.2.1 192.0.2.10 25\n"
        get_addrs.return_value = {
            "Wi-Fi": [SimpleNamespace(family=socket.AF_INET, address="198.51.100.10")]
        }

        self.assertIsNone(network_diagnostics.get_default_gateway("Wi-Fi"))
        self.assertEqual(run_cmd.call_count, 1)


if __name__ == "__main__":
    unittest.main()
