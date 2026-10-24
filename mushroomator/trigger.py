"""Weather-trigger model: when does a species fruit, given the weather of the previous weeks?

"Phenological niche" design (Capinha et al. 2019, 2024): dated observations are compared with random dates at
the same places. The model is additive (one spline per variable + logistic link), so each variable's
contribution can be shown to the user. It is exported as 1-D lookup tables read by the web application.
"""
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer

from . import features as feat
from .config import ASSETS_DIR, LAPSE_RATE, TRAIN_COUNTRIES, TRAIN_YEARS
from .sources import dem, gbif

FEATURES = ["doy", "T14", "P30", "P_7_21", "SWB"]
K_PSEUDO = 10
RNG_SEED = 42
TABLE_POINTS = 121


def model_dir():
    return ASSETS_DIR / "models"


# ------------------------------------------------------------------ data ----
@dataclass
class TrainingSet:
    X: pd.DataFrame        # features (temperatures moved to the observation's elevation)
    y: np.ndarray          # 1 = observation, 0 = random date at the same place
    year: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    season: tuple          # (first, last) day of year holding 95 % of the observations


def training_set(names, eo, extra_features=(), log=print):
    """Observations of `names` in the training countries, plus K random dates per observation."""
    rng = np.random.default_rng(RNG_SEED)
    occ = pd.concat([gbif.clean(gbif.occurrences(n, TRAIN_COUNTRIES, TRAIN_YEARS)) for n in names], ignore_index=True)
    i, j = eo.cell_of(occ.decimalLatitude, occ.decimalLongitude)
    occ["i"], occ["j"], occ["t"] = i, j, eo.day_index(occ.date.values)
    occ = occ[(occ.i >= 0) & (occ.j >= 0) & (occ.t >= feat.HISTORY_DAYS - 1) & (occ.t < len(eo.time))]
    occ = occ[np.isfinite(eo.tg[occ.t.values, occ.i.values, occ.j.values])]
    occ = occ.drop_duplicates(["i", "j", "t"]).reset_index(drop=True)
    occ["elev"] = dem.sample_points(occ.decimalLatitude.values, occ.decimalLongitude.values)
    occ["dz"] = (occ.elev - eo.elev[occ.i, occ.j]).fillna(0.0)
    doy = occ.date.dt.day_of_year.to_numpy()
    season = tuple(int(v) for v in np.percentile(doy, [2.5, 97.5]))
    log(f"    {len(occ)} observations datées, saison {season[0]}–{season[1]}")

    reps = np.repeat(np.arange(len(occ)), K_PSEUDO)
    years = rng.choice(occ.date.dt.year.to_numpy(), size=len(reps))
    days = rng.integers(1, 366, size=len(reps))
    dates = pd.to_datetime([f"{y}-01-01" for y in years]) + pd.to_timedelta(days - 1, unit="D")
    t = eo.day_index(dates.values)
    ok = (t >= feat.HISTORY_DAYS - 1) & (t < len(eo.time))
    pseudo = occ.iloc[reps[ok]][["i", "j", "dz", "decimalLatitude", "decimalLongitude"]].assign(t=t[ok], y=0)
    samples = pd.concat([occ[["i", "j", "dz", "decimalLatitude", "decimalLongitude", "t"]].assign(y=1), pseudo],
                        ignore_index=True).drop_duplicates(["i", "j", "t", "dz"])
    X = _sample_features(eo, samples, list(dict.fromkeys(FEATURES + list(extra_features))))
    when = eo.time[samples.t.values]
    return TrainingSet(X, samples.y.to_numpy(), when.astype("datetime64[Y]").astype(int) + 1970,
                       samples.decimalLatitude.to_numpy(), samples.decimalLongitude.to_numpy(), season)


def _sample_features(eo, samples, names, chunk=400):
    cells, cell_id = np.unique(samples[["i", "j"]].to_numpy(), axis=0, return_inverse=True)
    cell_id = cell_id.ravel()
    doy = (eo.time - eo.time.astype("datetime64[Y]")).astype(int) + 1
    out = {n: np.empty(len(samples)) for n in names}
    t = samples.t.to_numpy()
    for start in range(0, len(cells), chunk):
        block = cells[start:start + chunk]
        f = feat.compute(eo.rr[:, block[:, 0], block[:, 1]], eo.tg[:, block[:, 0], block[:, 1]], doy, eo.lat[block[:, 0]])
        sel = np.flatnonzero((cell_id >= start) & (cell_id < start + len(block)))
        for n in names:
            out[n][sel] = f[n][t[sel], cell_id[sel] - start]
    X = pd.DataFrame(out)
    for n in names:
        if feat.is_temperature(n) and n != "dT7":
            X[n] += LAPSE_RATE * samples.dz.to_numpy()
    return X


# ----------------------------------------------------------------- model ----
def make_model(names, C=0.5):
    parts = []
    for n in names:
        if n == "doy":
            spline = SplineTransformer(degree=3, extrapolation="periodic", knots=np.linspace(1, 366, 13)[:, None])
        else:
            spline = SplineTransformer(n_knots=6, degree=3, extrapolation="constant", knots="quantile")
        parts.append((n, spline, [n]))
    return make_pipeline(ColumnTransformer(parts), LogisticRegression(C=C, max_iter=5000))


def cross_validate(ts, names, groups=None):
    """Out-of-fold decision values (leave one year out by default)."""
    groups = ts.year if groups is None else groups
    out = np.full(len(ts.y), np.nan)
    for g in np.unique(groups):
        test = groups == g
        if ts.y[test].sum() < 5 or ts.y[~test].sum() < 30:
            continue
        m = make_model(names).fit(ts.X.loc[~test, names], ts.y[~test])
        out[test] = m.decision_function(ts.X.loc[test, names])
    return out


def in_season(ts):
    lo, hi = ts.season
    d = ts.X["doy"].to_numpy()
    return (d >= lo) & (d <= hi)


def auc(y, score, mask=None):
    ok = np.isfinite(score) if mask is None else (np.isfinite(score) & mask)
    return float(roc_auc_score(y[ok], score[ok])) if y[ok].min() != y[ok].max() else float("nan")


# ---------------------------------------------------------------- export ----
def export_tables(model, ts, names):
    """Exact additive decomposition as lookup tables: decision = intercept + sum(table_k(x_k))."""
    ref = {n: (1.0 if n == "doy" else float(np.nanmedian(ts.X[n]))) for n in names}
    base_row = pd.DataFrame([ref])[names]
    intercept = float(model.decision_function(base_row)[0])
    tables = {}
    for n in names:
        if n == "doy":
            xs = np.arange(1, 367, dtype=float)
        else:
            lo, hi = np.nanpercentile(ts.X[n], [0, 100])
            xs = np.linspace(lo, hi, TABLE_POINTS)
        rows = pd.DataFrame({k: np.full(len(xs), v) for k, v in ref.items()})[names]
        rows[n] = xs
        ys = model.decision_function(rows) - intercept
        tables[n] = {"x": np.round(xs, 3).tolist(), "y": np.round(ys, 4).tolist()}
    return intercept, ref, tables


def logit_from_tables(spec, X):
    """Decision value from exported tables (what the web application computes)."""
    total = np.full(len(X), spec["intercept"], dtype=float)
    for n in spec["features"]:
        tab = spec["tables"][n]
        total += np.interp(np.asarray(X[n], dtype=float), tab["x"], tab["y"])
    return total


def train(key, cfg, eo, region_bbox, log=print):
    ts = training_set(cfg["gbif"], eo, log=log)
    model = make_model(FEATURES).fit(ts.X[FEATURES], ts.y)
    intercept, ref, tables = export_tables(model, ts, FEATURES)
    spec = {"species": key, "features": FEATURES, "intercept": intercept, "reference": ref, "tables": tables,
            "season": list(ts.season)}
    # Percentile scale: decision values of random in-season dates (0.5 = an ordinary day of the season).
    season = in_season(ts)
    spec["quantiles"] = np.round(np.quantile(logit_from_tables(spec, ts.X[(ts.y == 0) & season]),
                                             np.linspace(0, 1, 101)), 4).tolist()
    oof = cross_validate(ts, FEATURES)
    oof_season_only = cross_validate(ts, ["doy"])
    w, s, e, n = region_bbox
    in_region = (ts.lon >= w) & (ts.lon <= e) & (ts.lat >= s) & (ts.lat <= n)
    spec["metrics"] = {
        "observations": int(ts.y.sum()),
        "observations_region": int(ts.y[in_region].sum()),
        "auc_annee_exclue": round(auc(ts.y, oof), 3),
        "auc_saison": round(auc(ts.y, oof, season), 3),
        "auc_saison_modele_saison_seule": round(auc(ts.y, oof_season_only, season), 3),
        "auc_saison_region": round(auc(ts.y, oof, season & in_region), 3),
    }
    spec["trained_on"] = {"weather": "E-OBS v30.0e (0,1°)", "observations": "GBIF " + "+".join(TRAIN_COUNTRIES),
                          "years": list(TRAIN_YEARS), "pseudo_absences_per_observation": K_PSEUDO}
    out = model_dir() / f"{key}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False))
    log(f"    AUC (année exclue) : {spec['metrics']['auc_annee_exclue']} ; en saison : "
        f"{spec['metrics']['auc_saison']} (saison seule : {spec['metrics']['auc_saison_modele_saison_seule']}) ; "
        f"Rhône-Alpes en saison : {spec['metrics']['auc_saison_region']}")
    return spec


def load(key):
    return json.loads((model_dir() / f"{key}.json").read_text())
