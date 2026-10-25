"""Points of the tests: `points` deduplicates the records (same taxon within ~10 m) and keeps the species plus 5 000
records of other forest fungi; `cas` keeps the points with LiDAR and terrain variables for the matched designs."""
import json, random, sys
from pathlib import Path

mode = sys.argv[1]
if mode == "points":                      # prepare_points.py points obs_raw.json points_sel.json
    seen, pts = set(), []
    for r in json.loads(Path(sys.argv[2]).read_text()):
        k = (r["groupe"], r["nom"], round(r["lat"], 4), round(r["lon"], 4))
        if k not in seen:
            seen.add(k); pts.append({**r, "id": len(pts)})
    sp = [p for p in pts if p["groupe"] not in ("groupe_cible", "hygrophore_mars")]
    bg = [p for p in pts if p["groupe"] == "groupe_cible"]
    random.Random(1).shuffle(bg)
    Path(sys.argv[3]).write_text(json.dumps(sp + bg[:5000]))
elif mode == "cas":                       # prepare_points.py cas points_sel.json features.json cases.json
    ok = {f["id"] for f in json.loads(Path(sys.argv[3]).read_text()) if "h_moy_25" in f and "tpi_50" in f}
    pts = [p for p in json.loads(Path(sys.argv[2]).read_text()) if p["id"] in ok]
    sp = [p for p in pts if p["groupe"] != "groupe_cible"]
    bg = [p for p in pts if p["groupe"] == "groupe_cible"]
    random.Random(2).shuffle(bg)
    Path(sys.argv[4]).write_text(json.dumps(sp + bg[:800]))
