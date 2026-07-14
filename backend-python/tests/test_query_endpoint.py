"""Contract tests for the Conversational Operational Query endpoint."""

from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.schemas.relief import OperationalQueryResponse
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False
else:
    FASTAPI_AVAILABLE = True


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed in this environment.")
class QueryEndpointTests(unittest.TestCase):
    @patch("app.core.llm_client.llm_client.answer_operational_query")
    def test_query_route_returns_structured_answer(self, mock_query) -> None:
        mock_response = OperationalQueryResponse(
            answer="Convoy 1 is currently in STAGING state with capacity of 80."
        )
        mock_query.return_value = mock_response

        client = TestClient(app)
        response = client.post("/query", json={"question": "What is the status of Convoy 1?"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["answer"], "Convoy 1 is currently in STAGING state with capacity of 80.")
        mock_query.assert_called_once()

    def test_query_route_requires_non_empty_question(self) -> None:
        client = TestClient(app)
        response = client.post("/query", json={"question": ""})
        self.assertEqual(response.status_code, 422)  # validation error
