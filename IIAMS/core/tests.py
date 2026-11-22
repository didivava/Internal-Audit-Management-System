from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase, override_settings


class ApplicationHealthTests(TestCase):
    @override_settings(DEBUG=True)
    def test_homepage_renders_the_existing_audit_workspace(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Internal audit management")
        self.assertContains(response, "/static/app.js")

    @override_settings(DEBUG=False)
    def test_production_homepage_does_not_expose_the_unsecured_prototype(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "Jordan Davis", status_code=503)

    def test_liveness_check_does_not_depend_on_database(self):
        response = self.client.get("/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_check_confirms_database_connectivity(self):
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "database": "ok"})

    @patch("core.views.connection.cursor", side_effect=OperationalError("database unavailable"))
    def test_readiness_check_returns_service_unavailable_without_leaking_details(self, cursor):
        with self.assertLogs("core.views", level="ERROR"):
            response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "not_ready"})
        self.assertNotIn("database unavailable", response.content.decode())
