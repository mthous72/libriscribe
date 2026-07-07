"""Tests for single-instance port selection and runtime UI state (Spec #1).

These exercise pure logic in libriscribe.server / libriscribe.runtime and need no
web framework dependencies.
"""
import unittest
from unittest import mock

import libriscribe.server as srv
import libriscribe.runtime as rt


class PortWalkTests(unittest.TestCase):
    def _patch(self, probe_map, free_set):
        return mock.patch.multiple(
            srv,
            _probe_health=lambda port, timeout=0.4: probe_map.get(port),
            _port_is_free=lambda port: port in free_set,
        )

    def test_existing_instance_on_first_port(self):
        # 8000 already serves LibriScribe -> open it, bind nothing.
        with self._patch({8000: "libriscribe"}, set()):
            self.assertEqual(srv._choose_port(), (None, 8000))

    def test_first_port_free(self):
        with self._patch({8000: None}, {8000}):
            self.assertEqual(srv._choose_port(), (8000, None))

    def test_fallback_when_first_port_taken_by_other(self):
        # Something non-LibriScribe holds 8000 -> fall back to 8001.
        with self._patch({8000: "", 8001: None}, {8001}):
            self.assertEqual(srv._choose_port(), (8001, None))

    def test_existing_instance_on_fallback_port(self):
        # Another app on 8000; an existing LibriScribe already fell back to 8001.
        with self._patch({8000: "", 8001: "libriscribe"}, set()):
            self.assertEqual(srv._choose_port(), (None, 8001))

    def test_no_free_port_and_no_instance(self):
        probe = {p: "" for p in srv.PORT_CANDIDATES}
        with self._patch(probe, set()):
            self.assertEqual(srv._choose_port(), (None, None))


class LocalHostResolutionTests(unittest.TestCase):
    """LIBRISCRIBE_HOST bind target -> the address used for the health probe + auto-open browser.
    A specific interface IP (e.g. a Tailscale 100.x) must NOT fall back to loopback, which uvicorn
    doesn't listen on when bound to that IP (regression: browser opened 127.0.0.1 -> refused)."""

    def test_default_loopback_stays_loopback(self):
        self.assertEqual(srv._local_host_for("127.0.0.1"), "127.0.0.1")

    def test_all_interfaces_reaches_via_loopback(self):
        self.assertEqual(srv._local_host_for("0.0.0.0"), "127.0.0.1")
        self.assertEqual(srv._local_host_for("::"), "127.0.0.1")
        self.assertEqual(srv._local_host_for(""), "127.0.0.1")

    def test_specific_ip_probes_that_ip_not_loopback(self):
        self.assertEqual(srv._local_host_for("100.125.124.123"), "100.125.124.123")


class RuntimeStateTests(unittest.TestCase):
    def setUp(self):
        rt.set_ui_state(dirty=False, active_generation=False)
        rt.shutdown_event.clear()

    def test_set_and_get(self):
        rt.set_ui_state(dirty=True)
        self.assertTrue(rt.get_ui_state()["dirty"])
        self.assertFalse(rt.get_ui_state()["active_generation"])

    def test_partial_update_keeps_other_fields(self):
        rt.set_ui_state(dirty=True)
        rt.set_ui_state(active_generation=True)
        state = rt.get_ui_state()
        self.assertTrue(state["dirty"])
        self.assertTrue(state["active_generation"])

    def test_request_shutdown_sets_event(self):
        self.assertFalse(rt.shutdown_event.is_set())
        rt.request_shutdown()
        self.assertTrue(rt.shutdown_event.is_set())


if __name__ == "__main__":
    unittest.main()
