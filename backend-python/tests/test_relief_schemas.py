"""Contract checks for ReliefGrid operational schemas."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from pydantic import ValidationError

from app.schemas.relief import (
    ConfidenceLevel,
    Convoy,
    ConvoyAssignment,
    ConvoyStatus,
    MissionBriefing,
    OperationalState,
    ReliefRequest,
    RequestStatus,
    RequestType,
)


class ReliefSchemaTests(unittest.TestCase):
    def test_operational_state_and_briefing_validate(self) -> None:
        timestamp = datetime.now(timezone.utc)
        state = OperationalState(
            scenario_id="central-london-demo",
            timestamp=timestamp,
            convoys=[Convoy(convoy_id="convoy-1", name="Westminster Support", lat=51.5014, lon=-0.1419, status=ConvoyStatus.STAGING, capacity=40)],
            requests=[ReliefRequest(request_id="req-med-sector-4", type=RequestType.MEDICAL, lat=51.5079, lon=-0.1280, priority=5, status=RequestStatus.OPEN, population_affected=120)],
        )
        briefing = MissionBriefing(
            briefing_id="briefing-1",
            timestamp=timestamp,
            crisis_assessment="Medical supplies are the immediate operational priority.",
            convoy_assignments=[ConvoyAssignment(convoy_id="convoy-1", request_id="req-med-sector-4", rationale="Shortest feasible response.")],
            confidence_level=ConfidenceLevel.HIGH,
            backup_plan="Hold convoy-2 in staging for the next urgent request.",
        )

        self.assertEqual(state.convoys[0].status, ConvoyStatus.STAGING)
        self.assertEqual(briefing.confidence_level, ConfidenceLevel.HIGH)

    def test_invalid_enum_and_priority_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReliefRequest(request_id="req-1", type="UNKNOWN", lat=51.5, lon=-0.14, priority=5, status=RequestStatus.OPEN, population_affected=1)
        with self.assertRaises(ValidationError):
            ReliefRequest(request_id="req-1", type=RequestType.MEDICAL, lat=51.5, lon=-0.14, priority=6, status=RequestStatus.OPEN, population_affected=1)
        with self.assertRaises(ValidationError):
            ReliefRequest(request_id="req-1", type=RequestType.MEDICAL, lat=51.5, lon=-0.14, priority="5", status=RequestStatus.OPEN, population_affected=1)
