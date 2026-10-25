"""Local controls for each record: random points 60-400 m away at the same distance to a road or path (BD TOPO),
so that the comparison bears on the place itself, not on where people walk."""
import concurrent.futures as cf, json, math, random, sys, time, urllib.request
from pathlib import Path
import shapely

cases, out, cache = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])
cache.mkdir(parents=True, exist_ok=True)
WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3:troncon_de_route"
       "&OUTPUTFORMAT=application/json&COUNT=3000&PROPERTYNAME=nature,geometrie&BBOX={s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326")
HALF = 700.0                                     # metres around the record for the path search

def paths(c):
    f = cache / f"{c['id']}.json"
    if not f.exists():
        dlat, dlon = HALF / 111320, HALF / (111320 * math.cos(math.radians(c["lat"])))
        url = WFS.format(s=c["lat"] - dlat, w=c["lon"] - dlon, n=c["lat"] + dlat, e=c["lon"] + dlon)
        for attempt in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mushroomator/0.1"}), timeout=90) as r:
                    f.write_bytes(r.read()); break
            except Exception:
                time.sleep(min(30, 2 ** attempt))
        else:
            return None
    try:
        return json.loads(f.read_text())["features"]
    except Exception:
        return None

def controls(c, k=4, candidates=120):
    feats = paths(c)
    if feats is None:
        return c, None, []
    kx = 111320 * math.cos(math.radians(c["lat"]))
    to_m = lambda lon, lat: ((lon - c["lon"]) * kx, (lat - c["lat"]) * 111320)
    lines = [shapely.LineString([to_m(x, y) for x, y, *_ in f["geometry"]["coordinates"]])
             for f in feats if f.get("geometry") and f["geometry"]["type"] == "LineString" and len(f["geometry"]["coordinates"]) > 1]
    if not lines:
        return c, None, []
    net = shapely.MultiLineString(lines)
    d_case = net.distance(shapely.Point(0, 0))
    rng = random.Random(c["id"])
    chosen = []
    for _ in range(candidates):
        r = math.sqrt(rng.uniform(60 ** 2, 400 ** 2)); a = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(a), r * math.sin(a)
        d = net.distance(shapely.Point(x, y))
        if abs(d - d_case) <= max(15.0, 0.3 * d_case):
            chosen.append({"lat": c["lat"] + y / 111320, "lon": c["lon"] + x / kx, "d_chemin": d})
            if len(chosen) == k:
                break
    return c, d_case, chosen

rows, t0 = [], time.time()
with cf.ThreadPoolExecutor(4) as pool:
    for i, (c, d_case, chosen) in enumerate(pool.map(controls, cases), 1):
        if d_case is None or len(chosen) < 2:
            continue
        rows.append({**c, "role": "cas", "strate": c["id"], "d_chemin": d_case})
        rows += [{"id": f"{c['id']}_{j}", "groupe": c["groupe"], "nom": c["nom"], "role": "temoin", "strate": c["id"], **ch}
                 for j, ch in enumerate(chosen)]
        if i % 200 == 0:
            print(f"{i}/{len(cases)} cas traités, {time.time() - t0:.0f} s", flush=True)
out.write_text(json.dumps(rows))
n_cases = sum(r["role"] == "cas" for r in rows)
print(f"{n_cases} cas gardés sur {len(cases)}, {len(rows) - n_cases} témoins")
