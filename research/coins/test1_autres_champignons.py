"""Do fine-scale variables (LiDAR HD canopy, terrain) tell each species' records from other forest fungi better than
coarse location and elevation? Out-of-fold AUC, spatial blocks of ~20 km, 3 random block-to-fold assignments."""
import json, math, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

pts = pd.DataFrame(json.loads(Path(sys.argv[1]).read_text()))
feat = pd.DataFrame(json.loads(Path(sys.argv[2]).read_text()))
hab = json.loads(Path(sys.argv[3]).read_text())
df = pts.merge(feat, on="id")
CANOPY = [f"{s}_{r}" for r in (10, 25, 50) for s in ("h_moy", "h_p90", "h_et", "trouees")]
TERRAIN = ["pente_5", "pente_25", "nordicite", "estitude", "tpi_25", "tpi_50", "tpi_100", "tpi_200", "courbure_10", "humidite_twi"]
COARSE = ["lat", "lon", "altitude"]
WOOD = {"Fomes fomentarius", "Fomitopsis pinicola", "Trametes versicolor", "Hypholoma fasciculare", "Armillaria mellea",
        "Calocera viscosa", "Mycena galericulata"}
n_all = len(df)
df = df.dropna(subset=CANOPY + TERRAIN).reset_index(drop=True)
print(f"points avec LiDAR HD et relief : {len(df)} / {n_all}")
kx, ky = df.lon * 111.32 * math.cos(math.radians(46.5)), df.lat * 111.32
df["bloc"] = (kx // 20).astype(int) * 100000 + (ky // 20).astype(int)

hgb = lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=20, l2_regularization=1.0)
logit = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000))

def folds(groups, seed):
    ub = np.unique(groups)
    f = dict(zip(ub, np.random.default_rng(seed).integers(0, 5, len(ub))))
    return np.array([f[g] for g in groups])

def oof(X, y, f, make):
    pred = np.full(len(y), np.nan)
    for k in range(5):
        tr, te = f != k, f == k
        if te.sum() == 0 or y[tr].sum() < 5:
            continue
        m = make().fit(X[tr], y[tr])
        pred[te] = m.predict_proba(X[te])[:, 1]
    ok = np.isfinite(pred)
    return roc_auc_score(y[ok], pred[ok]), pred

def evaluate(d, cols, make, seeds=(0, 1, 2)):
    X, y = d[cols].to_numpy(float), d.y.to_numpy()
    return [oof(X, y, folds(d.bloc.to_numpy(), s), make)[0] for s in seeds]

def top10_share(d, cols):
    """Share of the species' records among the 10 % best-rated places of the other fungi (10 % = chance), seed 0."""
    X, y = d[cols].to_numpy(float), d.y.to_numpy()
    _, pred = oof(X, y, folds(d.bloc.to_numpy(), 0), hgb)
    ok = np.isfinite(pred)
    threshold = np.quantile(pred[ok & (y == 0)], 0.9)
    return round(float((pred[ok & (y == 1)] > threshold).mean()), 3)

def group_importance(d, cols, groups):
    """AUC lost when a group of columns is shuffled in the held-out folds (seed 0)."""
    X, y = d[cols].to_numpy(float), d.y.to_numpy()
    f = folds(d.bloc.to_numpy(), 0)
    base, pred = oof(X, y, f, hgb)
    rng, drops = np.random.default_rng(0), {}
    models = {k: hgb().fit(X[f != k], y[f != k]) for k in range(5) if (f == k).any() and y[f != k].sum() >= 5}
    for name, gcols in groups.items():
        idx = [cols.index(c) for c in gcols]
        p2 = pred.copy()
        for k, m in models.items():
            te = np.where(f == k)[0]
            Xp = X[te].copy()
            Xp[:, idx] = Xp[rng.permutation(len(te))][:, idx]
            p2[te] = m.predict_proba(Xp)[:, 1]
        ok = np.isfinite(p2)
        drops[name] = round(base - roc_auc_score(y[ok], p2[ok]), 3)
    return drops

res = {}
species = [s for s in df.groupe.unique() if s != "groupe_cible"]
for bgname, bgmask in (("tous", df.groupe == "groupe_cible"), ("sol", (df.groupe == "groupe_cible") & ~df.nom.isin(WOOD))):
    for s in species:
        d = df[(df.groupe == s) | bgmask].copy()
        d["y"] = (d.groupe == s).astype(int)
        if d.y.sum() < 40:
            continue
        r = {"n": int(d.y.sum()), "n_fond": int((d.y == 0).sum())}
        for name, cols, make in (("grossier", COARSE, hgb), ("grossier+fin", COARSE + CANOPY + TERRAIN, hgb),
                                 ("fin_seul", CANOPY + TERRAIN, hgb), ("logit_grossier", COARSE, logit),
                                 ("logit_grossier+fin", COARSE + CANOPY + TERRAIN, logit)):
            a = evaluate(d, cols, make)
            r[name] = [round(float(np.mean(a)), 3), round(float(np.std(a)), 3)]
        r["top10_grossier"] = top10_share(d, COARSE)
        r["top10_grossier+fin"] = top10_share(d, COARSE + CANOPY + TERRAIN)
        if bgname == "tous":
            r["importance"] = group_importance(d, COARSE + CANOPY + TERRAIN, {"vegetation": CANOPY, "relief": TERRAIN, "position_altitude": COARSE})
        # region: habitat of the application (H) vs H + fine variables
        d["H"] = [hab[str(i)].get(s) if str(i) in hab else hab.get(i, {}).get(s) for i in d.id]
        reg = d[d.H.notna()].copy()
        if reg.y.sum() >= 15:
            r["region_n"] = int(reg.y.sum())
            r["region_auc_H_appli"] = round(float(roc_auc_score(reg.y, reg.H.astype(float))), 3)
            for name, cols in (("region_H+altitude", ["H", "altitude"]), ("region_H+altitude+fin", ["H", "altitude"] + CANOPY + TERRAIN)):
                a = evaluate(reg, cols, hgb)
                r[name] = round(float(np.mean(a)), 3)
        res[f"{s}|{bgname}"] = r
        print(s, bgname, json.dumps(r, ensure_ascii=False), flush=True)
Path(sys.argv[4]).write_text(json.dumps(res, ensure_ascii=False, indent=1))
