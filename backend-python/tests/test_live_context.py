"""Contract tests for the live context enrichment (weather and GDACS RSS alerts)."""

from __future__ import annotations

import unittest
from unittest.mock import patch, AsyncMock, MagicMock

try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.live_context import live_context_service
    from app.services.state_store import state_store
    from app.services.planner import planning_service
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False
else:
    FASTAPI_AVAILABLE = True


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed in this environment.")
class LiveContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_context_service_fetches_weather_and_alerts(self) -> None:
        # Mock weather response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "current_weather": {
                "temperature": 18.2,
                "weathercode": 0,
                "windspeed": 5.4,
            }
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            weather = await live_context_service.fetch_weather()
            self.assertEqual(weather.temperature, 18.2)
            self.assertEqual(weather.description, "Clear Sky")

        # Mock GDACS XML response
        mock_xml = """<?xml version="1.0" encoding="utf-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Mock Alert Title</title>
                    <description>Mock alert details.</description>
                    <link>https://mocklink.com</link>
                </item>
            </channel>
        </rss>
        """
        mock_xml_response = MagicMock()
        mock_xml_response.status_code = 200
        mock_xml_response.content = mock_xml.encode("utf-8")
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_xml_response
            alerts = await live_context_service.fetch_gdacs_alerts()
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0].title, "Mock Alert Title")

    def test_live_context_endpoint(self) -> None:
        client = TestClient(app)
        response = client.get("/live-context")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("weather", payload)
        self.assertIn("alerts", payload)
        self.assertGreater(payload["weather"]["temperature"], 0.0)

    @patch("app.services.ops_broadcaster.operations_broadcaster.broadcast_snapshot", new_callable=AsyncMock)
    def test_flood_surge_auto_generates_baseline_plan_if_missing(self, mock_broadcast: AsyncMock) -> None:
        # Clear prior plan
        planning_service._last_planning_response = None
        client = TestClient(app)
        response = client.post("/events/flood-surge")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(h["hazard_id"] == "haz-river-flood-surge" for h in payload["state"]["hazards"]))
