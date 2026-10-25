"""BD Forêt at the exact point (not the dominant group over 250 m): host group of the polygon containing the point,
the species' host value for it, and the distance to the forest edge (negative outside forest)."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(sys.argv[1]); sys.path.insert(0, str(ROOT))
import pyogrio.raw as raw, shapely  # noqa: E402
from pyproj import Transformer  # noqa: E402
from mushroomator import site  # noqa: E402
from mushroomator.hosts import group_of_tfv  # noqa: E402

pts = json.loads(Path(sys.argv[2]).read_text())
to_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
x, y = to_l93.transform([p["lon"] for p in pts], [p["lat"] for p in pts])
P = shapely.points(np.c_[x, y])
group = np.zeros(len(pts), dtype=int)
edge = np.full(len(pts), np.nan)
near = np.full(len(pts), np.inf)
for shp in sorted((ROOT / "data/raw/bdforet").glob("*/**/FORMATION_VEGETALE.shp")):
    meta, _, wkb, fields = raw.read(shp, columns=["CODE_TFV"])
    geoms = shapely.from_wkb(wkb)
    codes = np.array([group_of_tfv(c) for c in fields[0]])
    keep = codes > 0
    geoms, codes = geoms[keep], codes[keep]
    tree = shapely.STRtree(geoms)
    ip, ig = tree.query(P, predicate="within")
    group[ip] = codes[ig]
    edge[ip] = shapely.distance(P[ip], shapely.boundary(geoms[ig]))
    out = np.where(group == 0)[0]
    if len(out):
        j, d = tree.query_nearest(P[out], max_distance=500, return_distance=True)
        for a, dist in zip(out[j[0]], d):
            near[a] = min(near[a], dist)
    print(shp.parts[-5] if len(shp.parts) > 5 else shp, int((group > 0).sum()), flush=True)
dist = np.where(group > 0, edge, -np.minimum(near, 500))
species = site.species_payload("rhone-alpes")
res = {}
for i, p in enumerate(pts):
    r = {"groupe_bdf": int(group[i]), "dist_lisiere": None if not np.isfinite(dist[i]) else float(dist[i])}
    for sp in species:
        r[f"hote_{sp['key']}"] = float(sp["hotes"][group[i]])
    res[p["id"]] = r
Path(sys.argv[3]).write_text(json.dumps(res))
print("points en forêt BD Forêt :", int((group > 0).sum()), "/", len(pts))
