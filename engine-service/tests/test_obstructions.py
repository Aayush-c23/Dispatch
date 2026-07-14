"""Tests for the dynamic obstruction overlay and router."""

import pytest
from src.router import route_between_points, get_edges_in_radius
from src.obstructions import overlay

def test_obstruction_overlay():
    from src.router import _get_spatial_index
    import networkx as nx
    import random
    
    graph, _, node_ids = _get_spatial_index()
    
    # Find a path of at least 3 nodes to ensure there's a middle edge to block
    valid_path = None
    for _ in range(100):
        u = random.choice(node_ids)
        # Get nodes reachable from u
        reachable = nx.descendants(graph, u)
        if not reachable:
            continue
        v = random.choice(list(reachable))
        try:
            path = nx.shortest_path(graph, u, v)
            if len(path) > 3:
                valid_path = path
                break
        except nx.NetworkXNoPath:
            continue
            
    assert valid_path is not None, "Could not find a valid path of length > 3 in the graph"
    
    u = valid_path[0]
    v = valid_path[-1]
    
    lat1, lon1 = float(graph.nodes[u]["y"]), float(graph.nodes[u]["x"])
    lat2, lon2 = float(graph.nodes[v]["y"]), float(graph.nodes[v]["x"])

    # 1. Baseline route
    res1 = route_between_points(lat1, lon1, lat2, lon2)
    baseline_dist = res1.distance_meters
    baseline_edges = res1.edge_ids
    assert len(baseline_edges) > 0

    # 2. Block the middle of the route
    middle_edge = baseline_edges[len(baseline_edges)//2]
    overlay.apply_obstruction([middle_edge], "test-hazard")

    # 3. Reroute
    try:
        res2 = route_between_points(lat1, lon1, lat2, lon2)
        assert middle_edge not in res2.edge_ids
        assert res2.distance_meters >= baseline_dist
    except ValueError:
        # It's possible blocking this edge completely disconnects the nodes, which is fine
        pass

    # 4. Clear and reroute
    overlay.clear_obstruction("test-hazard")
    res3 = route_between_points(lat1, lon1, lat2, lon2)
    assert res3.distance_meters == baseline_dist

def test_stacking_hazards():
    overlay.clear_all()
    edge = "123-456"
    overlay.apply_obstruction([edge], "haz-1")
    overlay.apply_obstruction([edge], "haz-2")
    
    assert overlay.get_edge_overlay(edge)["blocked"] is True
    
    overlay.clear_obstruction("haz-1")
    assert overlay.get_edge_overlay(edge)["blocked"] is True
    
    overlay.clear_obstruction("haz-2")
    assert overlay.get_edge_overlay(edge) is None

def test_nopath():
    overlay.clear_all()
    # Find a destination point
    # Block all edges around the origin
    edges = get_edges_in_radius(51.503, -0.136, 500.0)
    overlay.apply_obstruction(edges, "massive-block")
    
    with pytest.raises(ValueError, match="No viable path"):
        route_between_points(51.503, -0.136, 51.512, -0.124)
