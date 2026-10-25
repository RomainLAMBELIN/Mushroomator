"""Stand-level controls: points 0.5-5 km from each record, at the same distance to a road or path (BD TOPO). Controls are
drawn along the path network (length-weighted) and offset sideways by the record's own distance to the nearest path."""
import concurrent.futures as cf, json, math, random, sys, time, urllib.request
from pathlib import Path
import shapely

strata, out, cache = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])
cases = [r for r in strata if r["role"] == "cas"]
WFS = ("https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=BDTOPO_V3:troncon_de_route"
       "&OUTPUTFORMAT=application/json&COUNT=5000&STARTINDEX={start}&PROPERTYNAME=geometrie&BBOX={s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326")
HALF = 5300.0

def network(c):
    f = cache / f"{c['id']}.json"
    if not f.exists():
        dlat, dlon = HALF / 111320, HALF / (111320 * math.cos(math.radians(c["lat"])))
        feats = []
        for page in range(3):
            url = WFS.format(start=5000 * page, s=c["lat"] - dlat, w=c["lon"] - dlon, n=c["lat"] + dlat, e=c["lon"] + dlon)
            for attempt in range(6):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mushroomator/0.1"}), timeout=120) as r:
                        got = json.loads(r.read()).get("features", []); break
                except Exception:
                    time.sleep(min(30, 2 ** attempt))
            else:
                return None
            feats += [g["geometry"]["coordinates"] for g in got if g.get("geometry") and g["geometry"]["type"] == "LineString"]
            if len(got) < 5000:
                break
        f.write_text(json.dumps(feats))
    return json.loads(f.read_text())

def controls(c, k=4, tries=400):
    coords = network(c)
    if not coords:
        return c, []
    kx = 111320 * math.cos(math.radians(c["lat"]))
    to_m = lambda lon, lat: ((lon - c["lon"]) * kx, (lat - c["lat"]) * 111320)
    lines = [shapely.LineString([to_m(x, y) for x, y, *_ in cs]) for cs in coords if len(cs) > 1]
    if not lines:
        return c, []
    net = shapely.MultiLineString(lines)
    tree = shapely.STRtree(lines)
    lengths = [l.length for l in lines]
    rng = random.Random(c["id"])
    d_case = c["d_chemin"]
    chosen = []
    for _ in range(tries):
        line = rng.choices(lines, weights=lengths)[0]
        t = rng.uniform(0, line.length)
        p, q = line.interpolate(max(0, t - 1)), line.interpolate(min(line.length, t + 1))
        nx, ny = -(q.y - p.y), q.x - p.x
        norm = math.hypot(nx, ny) or 1
        side = rng.choice((-1, 1))
        base = line.interpolate(t)
        x, y = base.x + side * d_case * nx / norm, base.y + side * d_case * ny / norm
        r = math.hypot(x, y)
        if not 500 <= r <= 5000:
            continue
        pt = shapely.Point(x, y)
        d = net.distance(pt) if d_case > 30 else lines[tree.nearest(pt)].distance(pt)
        if abs(d - d_case) <= max(15.0, 0.3 * d_case):
            chosen.append({"lat": c["lat"] + y / 111320, "lon": c["lon"] + x / kx, "d_chemin": d, "dist_cas": r})
            if len(chosen) == k:
                break
    return c, chosen

rows, t0 = [], time.time()
with cf.ThreadPoolExecutor(4) as pool:
    for i, (c, chosen) in enumerate(pool.map(controls, cases), 1):
        if len(chosen) >= 2:
            rows.append(c)
            rows += [{"id": f"{c['id']}_l{j}", "groupe": c["groupe"], "nom": c["nom"], "role": "temoin", "strate": c["strate"], **ch}
                     for j, ch in enumerate(chosen)]
        if i % 200 == 0:
            print(f"{i}/{len(cases)} cas, {time.time() - t0:.0f} s", flush=True)
out.write_text(json.dumps(rows))
print(sum(r["role"] == "cas" for r in rows), "cas gardés,", sum(r["role"] == "temoin" for r in rows), "témoins")
