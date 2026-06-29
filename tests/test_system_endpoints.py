"""Tests for the system endpoints: health, ui-state, shutdown (Spec #1).

Requires the FastAPI app dependencies (run in the standard test environment).
"""
import unittest

from fastapi.testclient import TestClient

from libriscribe.api.app import create_app
import libriscribe.runtime as rt


class SystemEndpointTests(unittest.TestCase):
    def setUp(self):
        rt.set_ui_state(dirty=False, active_generation=False)
        rt.shutdown_event.clear()
        self.client = TestClient(create_app())

    def test_health_identity(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["app"], "libriscribe")
        self.assertTrue(body["version"])

    def test_ui_state_roundtrip(self):
        resp = self.client.post("/api/ui-state", json={"dirty": True})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["dirty"])

        resp2 = self.client.get("/api/ui-state")
        self.assertTrue(resp2.json()["dirty"])

    def test_shutdown_requests_exit(self):
        self.assertFalse(rt.shutdown_event.is_set())
        resp = self.client.post("/api/shutdown")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "shutting_down")
        self.assertTrue(rt.shutdown_event.is_set())


if __name__ == "__main__":
    unittest.main()
