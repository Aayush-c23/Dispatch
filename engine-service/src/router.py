"""Route convoys over the local OpenStreetMap road graph."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import networkx as nx
from functools import lru_cache
from scipy.spatial import cKDTree

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


@lru_cache(maxsize=1)
def _get_spatial_index() -> tuple[nx.MultiDiGraph, cKDTree, list[int]]:
    graph = load_graph()
    nodes = list(graph.nodes(data=True))
    if not nodes:
        raise ValueError("Cannot route on an empty graph.")
    coords = [[float(data["y"]), float(data["x"])] for _, data in nodes]
    node_ids = [int(node_id) for node_id, _ in nodes]
    tree = cKDTree(coords)
    return graph, tree, node_ids


def _nearest_node(lat: float, lon: float) -> int:
    graph, tree, node_ids = _get_spatial_index()
    _, idx = tree.query([lat, lon])
    return node_ids[idx]


def get_edges_in_radius(lat: float, lon: float, radius_meters: float) -> list[str]:
    """Find all edge IDs within a physical radius of a lat/lon point."""
    graph, tree, node_ids = _get_spatial_index()
    
    # Rough approximation: 1 degree latitude is ~111.32km
    radius_degrees = radius_meters / 111320.0
    
    indices = tree.query_ball_point([lat, lon], r=radius_degrees)
    if not indices:
        return []
        
    found_nodes = {node_ids[i] for i in indices}
    edge_ids = set()
    
    # Find all edges incident to these nodes
    for u, v, k, data in graph.edges(keys=True, data=True):
        if u in found_nodes or v in found_nodes:
            if "edge_id" in data:
                edge_ids.add(str(data["edge_id"]))
                
    return list(edge_ids)


def k_routes_between_points(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    k: int = 3,
) -> list[RouteResult]:
    """Compute the fastest route and alternate routes using a penalty method."""

    graph, _, _ = _get_spatial_index()
    origin_node = _nearest_node(origin_lat, origin_lon)
    destination_node = _nearest_node(destination_lat, destination_lon)

    def haversine_heuristic(u: int, v: int) -> float:
        """Admissible heuristic for A* based on Haversine distance and max speed."""
        lat1, lon1 = float(graph.nodes[u]["y"]), float(graph.nodes[u]["x"])
        lat2, lon2 = float(graph.nodes[v]["y"]), float(graph.nodes[v]["x"])
        
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_meters = R * c
        
        return distance_meters / 33.3

    penalties = {}

    def penalized_weight(u: int, v: int, edge_attr: dict) -> float:
        w = routing_weight(u, v, edge_attr)
        if (u, v) in penalties:
            return w * penalties[(u, v)]
        return w

    routes = []
    
    # First search: the true fastest path
    try:
        node_ids = nx.astar_path(
            graph,
            origin_node,
            destination_node,
            heuristic=haversine_heuristic,
            weight=penalized_weight,
        )
    except nx.NetworkXNoPath:
        raise ValueError("No viable path exists between the specified points.")

    dist, time = _path_totals(graph, node_ids)
    routes.append(
        RouteResult(
            origin_node=origin_node,
            destination_node=destination_node,
            node_ids=[int(node_id) for node_id in node_ids],
            edge_ids=_path_edge_ids(graph, node_ids),
            geometry=_path_geometry(graph, node_ids),
            distance_meters=dist,
            estimated_seconds=time,
        )
    )

    if k <= 1:
        return routes

    # Penalize the first route's edges heavily to force divergence
    for u, v in zip(node_ids, node_ids[1:]):
        penalties[(u, v)] = 10.0

    attempts = 0
    max_attempts = k * 2
    
    while len(routes) < k and attempts < max_attempts:
        attempts += 1
        try:
            alt_node_ids = nx.astar_path(
                graph,
                origin_node,
                destination_node,
                heuristic=haversine_heuristic,
                weight=penalized_weight,
            )
        except nx.NetworkXNoPath:
            break
            
        # Check overlap with existing penalized edges
        overlap = sum(1 for u, v in zip(alt_node_ids, alt_node_ids[1:]) if (u, v) in penalties)
        total_edges = max(1, len(alt_node_ids) - 1)
        
        if overlap / total_edges > 0.8:
            # Too similar to an existing route, just penalize it more and try again
            for u, v in zip(alt_node_ids, alt_node_ids[1:]):
                penalties[(u, v)] = penalties.get((u, v), 1.0) * 3.0
            continue

        alt_dist, alt_time = _path_totals(graph, alt_node_ids)
        routes.append(
            RouteResult(
                origin_node=origin_node,
                destination_node=destination_node,
                node_ids=[int(node_id) for node_id in alt_node_ids],
                edge_ids=_path_edge_ids(graph, alt_node_ids),
                geometry=_path_geometry(graph, alt_node_ids),
                distance_meters=alt_dist,
                estimated_seconds=alt_time,
            )
        )

        for u, v in zip(alt_node_ids, alt_node_ids[1:]):
            penalties[(u, v)] = 10.0

    return routes

def route_between_points(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
) -> RouteResult:
    return k_routes_between_points(origin_lat, origin_lon, destination_lat, destination_lon, k=1)[0]
