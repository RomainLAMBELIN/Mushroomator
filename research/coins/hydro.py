"""Distance from each record and its controls to the nearest watercourse (BD TOPO), all and permanent only, capped at 700 m."""
import concurrent.futures as cf, json, math, sys, time, urllib.request
from pathlib import Path
import shapely

rows, out, cache = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])
cache.mkdir(parents=True, exist_ok=True)
WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3:troncon_hydrographique"
       "&OUTPUTFORMAT=application/json&COUNT=3000&PROPERTYNAME=persistance,geometrie&BBOX={s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326")
HALF, CAP = 1100.0, 700.0
strata = {}
for r in rows:
    strata.setdefault(r["strate"], []).append(r)

def run(item):
    sid, members = item
    case = next(m for m in members if m["role"] == "cas")
    f = cache / f"{sid}.json"
    if not f.exists():
        dlat, dlon = HALF / 111320, HALF / (111320 * math.cos(math.radians(case["lat"])))
        url = WFS.format(s=case["lat"] - dlat, w=case["lon"] - dlon, n=case["lat"] + dlat, e=case["lon"] + dlon)
        for attempt in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mushroomator/0.1"}), timeout=90) as r:
                    f.write_bytes(r.read()); break
            except Exception:
                time.sleep(min(30, 2 ** attempt))
        else:
            return {}
    feats = json.loads(f.read_text()).get("features", [])
    kx = 111320 * math.cos(math.radians(case["lat"]))
    to_m = lambda lon, lat: ((lon - case["lon"]) * kx, (lat - case["lat"]) * 111320)
    def net(perm):
        ls = [shapely.LineString([to_m(x, y) for x, y, *_ in g["geometry"]["coordinates"]]) for g in feats
              if g.get("geometry") and g["geometry"]["type"] == "LineString" and len(g["geometry"]["coordinates"]) > 1
              and (not perm or g["properties"].get("persistance") == "Permanent")]
        return shapely.MultiLineString(ls) if ls else None
    nets = {"d_eau": net(False), "d_eau_perm": net(True)}
    res = {}
    for m in members:
        p = shapely.Point(*to_m(m["lon"], m["lat"]))
        res[str(m["id"])] = {k: (min(CAP, n.distance(p)) if n is not None else CAP) for k, n in nets.items()}
    return res

allres = {}
with cf.ThreadPoolExecutor(4) as pool:
    for i, res in enumerate(pool.map(run, strata.items()), 1):
        allres.update(res)
        if i % 400 == 0:
            print(i, "strates", flush=True)
out.write_text(json.dumps([{"id": k, **v} for k, v in allres.items()]))
print(len(allres), "points avec distance à l'eau")
