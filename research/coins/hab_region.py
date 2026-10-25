"""Habitat score of the published application (host x elevation x pH, 250 m) at each point inside the region."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(sys.argv[1]); sys.path.insert(0, str(ROOT))
from mushroomator import layers, predict, site  # noqa: E402

pts = json.loads(Path(sys.argv[2]).read_text())
L = layers.load("rhone-alpes")
lat = np.array([p["lat"] for p in pts]); lon = np.array([p["lon"] for p in pts])
r, c = L.grid.index_of(lon, lat)
inside = r >= 0
out = {p["id"]: {} for p in pts}
for sp in site.species_payload("rhone-alpes"):
    H = predict.habitat(sp, L)
    v = np.full(len(pts), np.nan)
    v[inside] = H[r[inside], c[inside]]
    for p, x in zip(pts, v):
        out[p["id"]][sp["key"]] = None if not np.isfinite(x) else float(x)
Path(sys.argv[3]).write_text(json.dumps(out))
print("points dans la région :", int(inside.sum()), "/", len(pts))
