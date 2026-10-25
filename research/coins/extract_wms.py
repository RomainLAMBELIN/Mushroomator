"""Raw LiDAR HD canopy height (120 m at 1 m) and RGE ALTI terrain (400 m at 5 m) around each point, from the
Géoplateforme WMS (float32 BIL). One .npy per point and layer, so that the run can resume."""
import concurrent.futures as cf, json, math, sys, time, urllib.request
from pathlib import Path
import numpy as np

points, out = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
LAYERS = {"mnh": ("IGNF_LIDAR-HD_MNH_ELEVATION.ELEVATIONGRIDCOVERAGE.WGS84G", 60.0, 120),   # half-width (m), pixels
          "mnt": ("ELEVATION.ELEVATIONGRIDCOVERAGE.HIGHRES", 200.0, 80)}
URL = ("https://data.geopf.fr/wms-r?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={layer}&STYLES=&CRS=EPSG:4326"
       "&BBOX={s},{w},{n},{e}&WIDTH={px}&HEIGHT={px}&FORMAT=image/x-bil;bits=32")

def fetch(p, kind):
    path = out / f"{p['id']}_{kind}.npy"
    if path.exists():
        return "cache"
    layer, half, px = LAYERS[kind]
    dlat, dlon = half / 111320.0, half / (111320.0 * math.cos(math.radians(p["lat"])))
    url = URL.format(layer=layer, s=p["lat"] - dlat, w=p["lon"] - dlon, n=p["lat"] + dlat, e=p["lon"] + dlon, px=px)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mushroomator/0.1 (projet personnel)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
            if len(b) != px * px * 4:
                raise ValueError(f"taille {len(b)} : {b[:120]!r}")
            np.save(path, np.frombuffer(b, "<f4").reshape(px, px))
            return "ok"
        except Exception as e:
            last = e
            time.sleep(min(30, 2 ** attempt))
    return f"échec {last}"

jobs = [(p, k) for p in points for k in LAYERS]
done = {"ok": 0, "cache": 0, "échec": 0}
t0 = time.time()
with cf.ThreadPoolExecutor(int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
    for i, res in enumerate(pool.map(lambda j: fetch(*j), jobs), 1):
        done["échec" if res.startswith("échec") else res] += 1
        if res.startswith("échec") and done["échec"] <= 5:
            print(res[:300], flush=True)
        if i % 500 == 0 or i == len(jobs):
            print(f"{i}/{len(jobs)} {done} {time.time() - t0:.0f} s", flush=True)
