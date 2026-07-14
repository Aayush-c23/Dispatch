"""Pre-fetch the fixed OpenStreetMap graph used by the ReliefGrid demo.

This command is intentionally an offline build step. The routing service only
loads the resulting GraphML file and never calls OpenStreetMap during a demo.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import osmnx as ox


# Central London provides real roads, bridges, shelters, and dense alternate
# corridors while keeping graph download and route computation compact.
DEFAULT_BBOX = {
    "west": -0.1515,
    "south": 51.5000,
    "east": -0.1015,
    "north": 51.5235,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "road_network.graphml",
        help="GraphML path to create.",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "road_network.metadata.json",
        help="Companion metadata path to create.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = True
    ox.settings.log_console = True

    graph = ox.graph_from_bbox(
        bbox=(
            DEFAULT_BBOX["west"],
            DEFAULT_BBOX["south"],
            DEFAULT_BBOX["east"],
            DEFAULT_BBOX["north"],
        ),
        network_type="drive",
        simplify=True,
        retain_all=False,
    )
    graph = ox.add_edge_speeds(graph)
    graph = ox.add_edge_travel_times(graph)

    for u, v, key, attributes in graph.edges(keys=True, data=True):
        attributes["edge_id"] = f"{u}:{v}:{key}"
        attributes["status"] = "OPEN"
        attributes["hazard_multiplier"] = 1.0

    ox.save_graphml(graph, filepath=args.output)
    args.metadata_output.write_text(
        json.dumps(
            {
                "region": "Central London, United Kingdom",
                "bbox": DEFAULT_BBOX,
                "network_type": "drive",
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "generated_at": datetime.now(UTC).isoformat(),
                "source": "OpenStreetMap via OSMnx",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved {len(graph.nodes)} nodes and {len(graph.edges)} edges to {args.output}")


if __name__ == "__main__":
    main()
