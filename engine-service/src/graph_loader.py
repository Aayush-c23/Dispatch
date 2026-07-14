"""Load and prepare the local OpenStreetMap road graph for routing."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import networkx as nx
import osmnx as ox

from .obstructions import overlay

DEFAULT_GRAPH_PATH = Path(__file__).resolve().parents[1] / "data" / "road_network.graphml"


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _edge_blocked(data: dict[str, Any]) -> bool:
    status = str(data.get("status", "OPEN")).upper()
    return status in {"BLOCKED", "CLOSED", "IMPASSABLE"}


def _prepare_edge_attributes(graph: nx.MultiDiGraph) -> None:
    for u, v, key, data in graph.edges(keys=True, data=True):
        data["edge_id"] = str(data.get("edge_id") or f"{u}-{v}-{key}")
        data["status"] = str(data.get("status", "OPEN")).upper()
        data["length"] = _coerce_float(data.get("length"))

        travel_time = _coerce_float(data.get("travel_time"))
        if travel_time <= 0:
            speed_kph = _coerce_float(data.get("speed_kph"), 30.0)
            speed_mps = max(speed_kph * 1000 / 3600, 1.0)
            travel_time = data["length"] / speed_mps if data["length"] else 0.0

        multiplier = _coerce_float(data.get("hazard_multiplier"), 1.0)
        data["travel_time"] = travel_time * max(multiplier, 1.0)
        data["blocked"] = _edge_blocked(data)


@lru_cache(maxsize=1)
def load_graph(graph_path: str | Path = DEFAULT_GRAPH_PATH) -> nx.MultiDiGraph:
    """Load the local road graph and normalize routing attributes."""

    path = Path(graph_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Road graph not found at {path}. Run engine-service/scripts/fetch_road_network.py first."
        )

    graph = ox.load_graphml(path)
    _prepare_edge_attributes(graph)
    return graph


def routing_weight(_u: int, _v: int, edge_data: dict[str, Any]) -> float:
    """NetworkX weight callback that excludes blocked parallel edges (considering live overlay)."""

    usable_weights: list[float] = []
    for data in edge_data.values():
        edge_id = str(data.get("edge_id", ""))
        live_data = overlay.get_edge_overlay(edge_id) if edge_id else None
        
        is_blocked = live_data["blocked"] if live_data else data.get("blocked")
        if is_blocked:
            continue
            
        travel_time = _coerce_float(data.get("travel_time"))
        length = _coerce_float(data.get("length"))
        base_weight = travel_time if travel_time > 0 else length
        
        multiplier = live_data["hazard_multiplier"] if live_data else 1.0
        usable_weights.append(base_weight * max(multiplier, 1.0))

    return min(usable_weights) if usable_weights else float("inf")
