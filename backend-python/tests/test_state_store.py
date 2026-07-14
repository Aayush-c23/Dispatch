"""Focused tests for the deterministic operational-state store."""

from __future__ import annotations

import unittest

from app.schemas.relief import Hazard, HazardType, RequestStatus
from app.services.state_store import OperationalStateStore, StateStoreError, build_seed_state


class OperationalStateStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = OperationalStateStore(build_seed_state())

    def test_seed_state_has_stable_demo_entities(self) -> None:
        state = self.store.get_state()
        self.assertEqual(state.scenario_id, "central-london-relief-demo")
        self.assertEqual({convoy.convoy_id for convoy in state.convoys}, {"convoy-1", "convoy-2", "convoy-3", "convoy-4", "convoy-5", "convoy-6"})
        self.assertIn("req-med-sector-4", {request.request_id for request in state.requests})

    def test_assignment_updates_convoy_and_request_without_leaking_state(self) -> None:
        updated = self.store.update_convoy_assignment("convoy-1", "req-evac-elm-shelter")
        convoy = next(item for item in updated.convoys if item.convoy_id == "convoy-1")
        request = next(item for item in updated.requests if item.request_id == "req-evac-elm-shelter")

        self.assertEqual(convoy.current_request_id, "req-evac-elm-shelter")
        self.assertEqual(convoy.status.value, "EVACUATING")
        self.assertEqual(request.status, RequestStatus.ASSIGNED)
        updated.convoys[0].name = "external mutation"
        self.assertNotEqual(self.store.get_state().convoys[0].name, "external mutation")
        with self.assertRaises(StateStoreError):
            self.store.update_convoy_assignment("convoy-2", "req-evac-elm-shelter")

    def test_hazard_and_request_mutations_validate_ids(self) -> None:
        updated = self.store.add_hazard(Hazard(hazard_id="haz-bridge-7-collapse", edge_ids=["bridge-7-edge"], type=HazardType.COLLAPSE, severity=5))
        self.assertIn("haz-bridge-7-collapse", {hazard.hazard_id for hazard in updated.hazards})
        state = self.store.update_request_status("req-med-sector-4", RequestStatus.IN_PROGRESS)
        request = next(item for item in state.requests if item.request_id == "req-med-sector-4")
        self.assertEqual(request.status, RequestStatus.IN_PROGRESS)
        with self.assertRaises(StateStoreError):
            self.store.update_convoy_assignment("missing-convoy", "req-med-sector-4")

    def test_snapshot_is_json_compatible(self) -> None:
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["scenario_id"], "central-london-relief-demo")
        self.assertIsInstance(snapshot["timestamp"], str)
        self.assertEqual(snapshot["convoys"][0]["convoy_id"], "convoy-1")
