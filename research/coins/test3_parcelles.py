"""Stand level: can these variables tell the place of a record from random forest places 0.5-5 km away at the same
distance to a road or path? Within-stratum AUC (each record against its own controls), spatial block cross-validation."""
import json, math, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

strata = pd.DataFrame(json.loads(Path(sys.argv[1]).read_text()))
feats = pd.concat([pd.DataFrame(json.loads(Path(f).read_text())) for f in sys.argv[2].split(",")])
feats["id"] = feats["id"].astype(str)
strata["id"] = strata["id"].astype(str)
df = strata.merge(feats.drop_duplicates("id"), on="id", how="left")
bdf = json.loads(Path(sys.argv[5]).read_text())
for c in ("groupe_bdf", "dist_lisiere"):
    df[c] = [bdf.get(i, {}).get(c) for i in df["id"]]
df["hote"] = [bdf.get(i, {}).get(f"hote_{g}") for i, g in zip(df["id"], df["groupe"])]
CANOPY = [f"{s}_{r}" for r in (10, 25, 50) for s in ("h_moy", "h_p90", "h_et", "trouees")]
TERRAIN = ["pente_5", "pente_25", "nordicite", "estitude", "tpi_25", "tpi_50", "tpi_100", "tpi_200", "courbure_10", "humidite_twi"]
FEATS = CANOPY + TERRAIN + ["altitude"]
WATER = []
FOREST = ["hote", "dist_lisiere"]
df = df.dropna(subset=FEATS)
df = df[df.h_moy_25 >= 3]                                          # within forest only, cases and controls alike
df["y"] = (df.role == "cas").astype(int)
keep = df.groupby("strate").y.agg(["sum", "count"])
df = df[df.strate.isin(keep[(keep["sum"] == 1) & (keep["count"] >= 3)].index)].copy()
case_xy = df[df.y == 1].set_index("strate")[["lat", "lon"]]
df["bloc"] = df.strate.map(lambda s: (int(case_xy.lon[s] * 111.32 * math.cos(math.radians(46.5)) // 20), int(case_xy.lat[s] * 111.32 // 20)))
for c in FEATS + WATER + FOREST:                                   # contrasts within each stratum
    df[c + "_d"] = df[c] - df.groupby("strate")[c].transform("mean")
CENTRED = [c + "_d" for c in FEATS]

def within_auc(d, score):
    d = d.assign(s=score)
    res = []
    for _, g in d.groupby("strate"):
        c = g.s[g.y == 1].iloc[0]; t = g.s[g.y == 0]
        res.append(((c > t).mean() + 0.5 * (c == t).mean()))
    return float(np.mean(res))

hgb = lambda: HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=3, min_samples_leaf=30, l2_regularization=1.0)
logit = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000))

def cv(d, cols, make, seeds=(0, 1, 2)):
    out = []
    blocks = d.bloc.unique()
    for seed in seeds:
        fold = dict(zip(blocks, np.random.default_rng(seed).integers(0, 5, len(blocks))))
        f = d.bloc.map(fold).to_numpy()
        score = np.full(len(d), np.nan)
        for k in range(5):
            tr, te = f != k, f == k
            if te.sum() == 0:
                continue
            m = make().fit(d[cols].to_numpy(float)[tr], d.y.to_numpy()[tr])
            score[te] = m.predict_proba(d[cols].to_numpy(float)[te])[:, 1]
        out.append(within_auc(d, score))
    return round(float(np.mean(out)), 3), round(float(np.std(out)), 3)

res = {}
groups = [g for g in df.groupe.unique()]
general = df[df.groupe == "groupe_cible"]
gen_model = {name: make().fit(general[cols].to_numpy(float), general.y) for name, cols, make in
             (("hgb_contrastes", CENTRED, hgb), ("logit_contrastes", CENTRED, logit))}
for g in groups + ["toutes_especes"]:
    d = df[df.groupe != "groupe_cible"] if g == "toutes_especes" else df[df.groupe == g]
    n = int(d.y.sum())
    if n < 40:
        continue
    r = {"strates": n, "temoins": int((d.y == 0).sum())}
    r["hgb_brut"] = cv(d, FEATS, hgb)
    r["hgb_contrastes"] = cv(d, CENTRED, hgb)
    r["logit_contrastes"] = cv(d, CENTRED, logit)
    r["logit_contrastes_vegetation"] = cv(d, [c + "_d" for c in CANOPY], logit)
    r["logit_contrastes_relief"] = cv(d, [c + "_d" for c in TERRAIN + ["altitude"]], logit)
    reg = d[d.groupby("strate").hote.transform(lambda v: v.notna().all() and (v > 0).all())]   # BD Forêt everywhere in the stratum
    if g != "groupe_cible" and reg.y.sum() >= 30:
        cols = CENTRED + [c + "_d" for c in WATER]
        r["region_strates"] = int(reg.y.sum())
        r["region_logit_contrastes"] = cv(reg, cols, logit)
        r["region_logit_+hote_lisiere"] = cv(reg, cols + [c + "_d" for c in FOREST], logit)
        r["region_hote_seul"] = round(within_auc(reg, reg.hote.to_numpy(float)), 3)
    if g != "groupe_cible":                                        # model of "fungi in general" applied to the species
        for name, m in gen_model.items():
            cols = CENTRED
            r[f"general_{name}"] = round(within_auc(d, m.predict_proba(d[cols].to_numpy(float))[:, 1]), 3)
    res[g] = r
    print(g, json.dumps(r), flush=True)
lg = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000)).fit(general[CENTRED].to_numpy(float), general.y)
coef = dict(zip(FEATS, np.round(lg[-1].coef_[0], 3)))
res["coefficients_champignons_en_general"] = coef
print("coefficients (contrastes standardisés), champignons en général :", json.dumps(dict(sorted(coef.items(), key=lambda kv: -abs(kv[1])))))
Path(sys.argv[3]).write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))
