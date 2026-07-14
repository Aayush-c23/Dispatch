"""Smoke tests for deterministic convoy assignment."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.assignment_solver import solve_assignments


def fake_route(origin_lat: float, _origin_lon: float, destination_lat: float, _destination_lon: float) -> SimpleNamespace:
    eta = abs(destination_lat - origin_lat) * 1_000
    return SimpleNamespace(
        estimated_seconds=eta,
        to_dict=lambda: {"estimated_seconds": eta, "distance_meters": eta * 10},
    )


class AssignmentSolverTests(unittest.TestCase):
    def test_prioritizes_urgent_request_and_skips_unavailable_convoys(self) -> None:
        assignments = solve_assignments(
            convoys=[
                {"convoy_id": "convoy-available", "lat": 51.50, "lon": -0.14, "status": "STAGING", "capacity": 30, "current_request_id": None},
                {"convoy_id": "convoy-blocked", "lat": 51.51, "lon": -0.14, "status": "BLOCKED", "capacity": 100, "current_request_id": None},
            ],
            requests=[
                {"request_id": "req-low", "lat": 51.501, "lon": -0.13, "priority": 2, "status": "OPEN", "population_affected": 900},
                {"request_id": "req-high", "lat": 51.502, "lon": -0.13, "priority": 5, "status": "OPEN", "population_affected": 20},
            ],
            route_provider=fake_route,
        )

        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].convoy_id, "convoy-available")
        self.assertEqual(assignments[0].request_id, "req-high")
        self.assertEqual(assignments[0].to_action()["action_type"], "ASSIGN")

    def test_skips_convoys_that_cannot_meet_declared_demand(self) -> None:
        assignments = solve_assignments(
            convoys=[{"convoy_id": "convoy-small", "lat": 51.50, "lon": -0.14, "status": "STAGING", "capacity": 5, "current_request_id": None}],
            requests=[{"request_id": "req-demanding", "lat": 51.51, "lon": -0.13, "priority": 5, "status": "OPEN", "population_affected": 20, "required_capacity": 10}],
            route_provider=fake_route,
        )
        self.assertEqual(assignments, [])
