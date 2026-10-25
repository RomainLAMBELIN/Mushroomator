"""Are spots persistent? For records of 2021 onwards, does an earlier record of the same species nearby (by another
observer) single out the species' records among those of other forest fungi made the same years?"""
import json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import BallTree

rows = json.loads(Path(sys.argv[1]).read_text())
seen, recs = set(), []
for r in rows:
    k = (r["groupe"], round(r["lat"], 4), round(r["lon"], 4), (r.get("date") or "")[:10])
    if k not in seen and r.get("annee"):
        seen.add(k); recs.append(r)
lat = np.radians([r["lat"] for r in recs]); lon = np.radians([r["lon"] for r in recs])
X = np.c_[lat, lon]
year = np.array([r["annee"] for r in recs]); grp = np.array([r["groupe"] for r in recs])
author = np.array([(r.get("auteur") or "").strip().lower() for r in recs])
test = year >= 2021
species = [g for g in sorted(set(grp)) if g != "groupe_cible"]
R_EARTH = 6371000.0
res = {}
for s in species:
    past = np.where((grp == s) & (year < 2021))[0]
    pos, neg = np.where(test & (grp == s))[0], np.where(test & (grp == "groupe_cible"))[0]
    if len(past) < 20 or len(pos) < 20:
        continue
    tree = BallTree(X[past], metric="haversine")
    def nearest(idx, other_observer):
        d, j = tree.query(X[idx], k=min(30, len(past)))
        out = np.full(len(idx), 20000.0)
        for a, (dd, jj) in enumerate(zip(d, j)):
            for dist, k in zip(dd, jj):
                p = past[k]
                if year[p] >= year[idx[a]]:
                    continue
                if other_observer and author[idx[a]] and author[p] == author[idx[a]]:
                    continue
                out[a] = dist * R_EARTH; break
        return out
    r = {"anciennes": int(len(past)), "test_espece": int(len(pos)), "test_autres": int(len(neg))}
    for other in (True, False):
        dp, dn = nearest(pos, other), nearest(neg, other)
        tag = "autre_observateur" if other else "tout_observateur"
        y = np.r_[np.ones(len(dp)), np.zeros(len(dn))]
        r[f"auc_{tag}"] = round(float(roc_auc_score(y, -np.r_[dp, dn])), 3)
        for R in (100, 250, 500, 1000):
            a, b = (dp <= R).mean(), (dn <= R).mean()
            r[f"{tag}_{R}m"] = [round(float(a), 3), round(float(b), 3)]
    res[s] = r
    print(s, json.dumps(r), flush=True)
Path(sys.argv[2]).write_text(json.dumps(res, indent=1))
