import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app


class DummyOrchestrator:
    def __init__(self, response):
        self._response = response

    def ask(self, prompt):
        return self._response


class DummyResponse:
    def __init__(self, text):
        self.text = text


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)

    def test_root_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json())

    def test_ui_route(self):
        response = self.client.get("/ui")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Metis Intelligence", response.text)
        self.assertIn("Oracle Tablet for High-Signal Discovery", response.text)
        self.assertIn("Tablet of Inquiry", response.text)
        self.assertIn("Invoke Insight", response.text)
        self.assertIn("Revealed Bulletin", response.text)
        self.assertNotIn("Run Discovery", response.text)

    def test_domains_route(self):
        response = self.client.get("/domains")
        self.assertEqual(response.status_code, 200)
        self.assertIn("1", response.json())

    def test_research_route_accepts_string_response(self):
        with patch.object(app, "get_metis_orchestrator", return_value=DummyOrchestrator("plain text report")):
            response = self.client.post("/research", json={"domain_id": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["report"], "plain text report")
        self.assertIn("style_hint", response.json())

    def test_research_route_accepts_object_with_text(self):
        with patch.object(app, "get_metis_orchestrator", return_value=DummyOrchestrator(DummyResponse("object report"))):
            response = self.client.post("/research", json={"domain_id": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["report"], "object report")

    def test_custom_domain_requires_value(self):
        response = self.client.post("/research", json={"domain_id": "9"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Custom domain is required", response.text)


if __name__ == "__main__":
    unittest.main()
