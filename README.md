# ReliefGrid AI

## Road-network data

The routing engine is designed to run from a pre-fetched OpenStreetMap graph,
so it has no external map-data dependency during a demonstration. The demo
region is Central London (a compact 0.05° by 0.0235° area around Westminster,
Trafalgar Square, and the River Thames).

From the repository root, create the graph once:

```powershell
python -m pip install -r engine-service/requirements.txt
python engine-service/scripts/fetch_road_network.py
```

This writes `engine-service/data/road_network.graphml` and accompanying
metadata. Graph data is excluded from version control because it is derived
from OpenStreetMap and can be regenerated with the command above.
