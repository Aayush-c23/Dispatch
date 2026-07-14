"""Route convoys over the local OpenStreetMap road graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from .graph_loader import load_graph, routing_weight


@dataclass(frozen=True)
class RouteResult:
    origin_node: int
    destination_node: int
    node_ids: list[int]
    edge_ids: list[str]
    geometry: list[dict[str, float]]
    distance_meters: float
    estimated_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_node": self.origin_node,
            "destination_node": self.destination_node,
            "node_ids": self.node_ids,
            "edge_ids": self.edge_ids,
            "geometry": self.geometry,
            "distance_meters": round(self.distance_meters, 1),
            "estimated_seconds": round(self.estimated_seconds, 1),
        }


def _best_edge_data(graph: nx.MultiDiGraph, u: int, v: int) -> dict[str, Any]:
    edge_options = graph.get_edge_data(u, v)
    if not edge_options:
        return {}

    usable_edges = [
        data
        for data in edge_options.values()
        if not data.get("blocked") and routing_weight(u, v, {0: data}) != float("inf")
    ]
    if not usable_edges:
        return {}

    return min(
        usable_edges,
        key=lambda data: float(data.get("travel_time") or data.get("length") or 0.0),
    )


def _path_edge_ids(graph: nx.MultiDiGraph, node_ids: list[int]) -> list[str]:
    edge_ids: list[str] = []
    for u, v in zip(node_ids, node_ids[1:]):
        data = _best_edge_data(graph, u, v)
        edge_ids.append(str(data.get("edge_id", f"{u}-{v}")))
    return edge_ids


def _path_geometry(graph: nx.MultiDiGraph, node_ids: list[int]) -> list[dict[str, float]]:
    return [
        {"lat": float(graph.nodes[node_id]["y"]), "lon": float(graph.nodes[node_id]["x"])}
        for node_id in node_ids
    ]


def _path_totals(graph: nx.MultiDiGraph, node_ids: list[int]) -> tuple[float, float]:
    distance_meters = 0.0
    estimated_seconds = 0.0
    for u, v in zip(node_ids, node_ids[1:]):
        data = _best_edge_data(graph, u, v)
        distance_meters += float(data.get("length") or 0.0)
        estimated_seconds += float(data.get("travel_time") or 0.0)
    return distance_meters, estimated_seconds


def _nearest_node(graph: nx.MultiDiGraph, lat: float, lon: float) -> int:
    nearest_id: int | None = None
    nearest_distance = float("inf")
    for node_id, data in graph.nodes(data=True):
        node_lat = float(data["y"])
        node_lon = float(data["x"])
        distance = (node_lat - lat) ** 2 + (node_lon - lon) ** 2
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_id = int(node_id)

    if nearest_id is None:
        raise ValueError("Cannot route on an empty graph.")
    return nearest_id


def route_between_points(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
) -> RouteResult:
    """Compute the fastest route between two latitude/longitude points."""

    graph = load_graph()
    origin_node = _nearest_node(graph, origin_lat, origin_lon)
    destination_node = _nearest_node(graph, destination_lat, destination_lon)

    node_ids = nx.shortest_path(
        graph,
        origin_node,
        destination_node,
        weight=routing_weight,
        method="dijkstra",
    )

    distance_meters, estimated_seconds = _path_totals(graph, node_ids)
    return RouteResult(
        origin_node=origin_node,
        destination_node=destination_node,
        node_ids=[int(node_id) for node_id in node_ids],
        edge_ids=_path_edge_ids(graph, node_ids),
        geometry=_path_geometry(graph, node_ids),
        distance_meters=distance_meters,
        estimated_seconds=estimated_seconds,
    )
