"""Fine-scale variables around each point from the LiDAR HD canopy height (1 m) and the RGE ALTI terrain (5 m)."""
import json, math, sys
from pathlib import Path
import numpy as np

points, wms, out = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), Path(sys.argv[3])

def disk(n, radius_px):
    c = (n - 1) / 2
    y, x = np.mgrid[:n, :n]
    return (x - c) ** 2 + (y - c) ** 2 <= radius_px ** 2

MNH_N, MNT_N, MNT_RES = 120, 80, 5.0
DISKS_H = {r: disk(MNH_N, r) for r in (10, 25, 50)}
DISKS_T = {r: disk(MNT_N, r / MNT_RES) for r in (25, 50, 100, 200)}
OFFS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

def canopy(h):
    valid = (h > -2) & (h < 70)
    f = {}
    for r, m in DISKS_H.items():
        v = h[m & valid]
        if v.size < 0.7 * m.sum():
            return None                        # outside LiDAR HD coverage (or mostly invalid)
        v = np.clip(v, 0, None)
        f |= {f"h_moy_{r}": v.mean(), f"h_p90_{r}": np.percentile(v, 90), f"h_et_{r}": v.std(), f"trouees_{r}": (v < 2).mean()}
    return f

def flow_accumulation(z):
    """D8 upslope area (cells) within the window: each cell drains to its steepest lower neighbour."""
    n = z.shape[0]
    pad = np.pad(z, 1, mode="edge")
    drops = np.stack([(z - pad[1 + dy:1 + dy + n, 1 + dx:1 + dx + n]) / math.hypot(dy, dx) for dy, dx in OFFS])
    best = drops.argmax(0)
    has = drops.max(0) > 0
    acc = np.ones(n * n)
    order = np.argsort(-z, axis=None)
    dy = np.array([o[0] for o in OFFS])[best].ravel(); dx = np.array([o[1] for o in OFFS])[best].ravel()
    rows, cols = np.divmod(np.arange(n * n), n)
    rcv = np.where(has.ravel(), np.clip(rows + dy, 0, n - 1) * n + np.clip(cols + dx, 0, n - 1), -1)
    for i in order:
        if rcv[i] >= 0:
            acc[rcv[i]] += acc[i]
    return acc.reshape(n, n)

def terrain(z):
    if not np.isfinite(z).all() or (z < -100).any() or (z > 5000).any():
        return None
    n, c = MNT_N, MNT_N // 2
    centre = z[c - 1:c + 1, c - 1:c + 1].mean()
    f = {"altitude": centre}
    # slope and aspect from a plane fitted within 25 m
    m = DISKS_T[25]
    yy, xx = np.mgrid[:n, :n]
    X = np.c_[(xx[m] - (n - 1) / 2) * MNT_RES, ((n - 1) / 2 - yy[m]) * MNT_RES, np.ones(m.sum())]
    gx, gy, _ = np.linalg.lstsq(X, z[m], rcond=None)[0]           # dz/dx (east), dz/dy (north)
    slope = math.degrees(math.atan(math.hypot(gx, gy)))
    f["pente_25"] = slope
    if slope > 2:
        aspect = math.atan2(-gx, -gy)                              # direction the slope faces (0 = north)
        f["nordicite"], f["estitude"] = math.cos(aspect), math.sin(aspect)
    else:
        f["nordicite"] = f["estitude"] = 0.0
    w = z[c - 2:c + 2, c - 2:c + 2]
    f["pente_5"] = math.degrees(math.atan(np.hypot(*np.gradient(w, MNT_RES)).mean()))
    for r, m in DISKS_T.items():
        f[f"tpi_{r}"] = centre - z[m].mean()                       # < 0: hollow, > 0: ridge
    f["courbure_10"] = (z[c + 2, c] + z[c - 2, c] + z[c, c + 2] + z[c, c - 2] - 4 * z[c, c]) / (2 * MNT_RES) ** 2
    acc = flow_accumulation(z)
    a = acc[c - 2:c + 2, c - 2:c + 2].max() * MNT_RES ** 2
    f["humidite_twi"] = math.log(a / MNT_RES / math.tan(math.radians(max(slope, 0.5))))
    return f

rows, missing = [], {"mnh": 0, "mnt": 0}
for p in points:
    row = {"id": p["id"]}
    for kind, fn in (("mnh", canopy), ("mnt", terrain)):
        path = wms / f"{p['id']}_{kind}.npy"
        f = fn(np.load(path)) if path.exists() else None
        if f is None:
            missing[kind] += 1
        else:
            row |= {k: float(v) for k, v in f.items()}
    rows.append(row)
out.write_text(json.dumps(rows))
print(f"{len(rows)} points ; sans LiDAR HD exploitable : {missing['mnh']} ; sans relief : {missing['mnt']}")
