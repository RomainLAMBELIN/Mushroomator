"""Feasibility study: does antecedent weather predict *when* a species is observed fruiting?

Design ("phenological niche", after Capinha et al. 2024, BioScience):
  - positives: dated GBIF observations (one per 0.1° cell and day);
  - temporal pseudo-absences: same cell, K random dates inside the species' season window
    (any year of the study period);
  - features: lagged precipitation sums, mean temperatures, a soil-water bucket index;
  - models: seasonal null (day-of-year + location) vs. weather vs. both;
  - validation: leave-one-year-out (temporal) and 2°-block (spatial) cross-validation.

Usage: python feasibility.py EOBS_NPZ GBIF_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

RNG = np.random.default_rng(42)
K_PSEUDO = 10          # pseudo-absences per positive
WMAX = 120.0           # bucket capacity (mm), typical forest-soil available water
SPECIES = {
    "Boletus_edulis": "Cèpe de Bordeaux",
    "Cantharellus_cibarius": "Girolle",
    "Craterellus_cornucopioides": "Trompette de la mort",
    "Hydnum_repandum": "Pied de mouton",
    "Macrolepiota_procera": "Coulemelle",
    "Morchella": "Morilles",
}
RAIN_WINDOWS = [1, 3, 7, 14, 21, 30, 45, 60]
LAGGED_RAIN = [(7, 14), (14, 21), (21, 28), (28, 42)]   # rain fallen between b and a days before t
TEMP_WINDOWS = [3, 7, 14, 21, 30]


# ---------------------------------------------------------------- weather ----
class Weather:
    def __init__(self, npz_path):
        z = np.load(npz_path)
        self.rr, self.tg = z["rr"], z["tg"]
        self.time = z["time"].astype("datetime64[D]")
        self.lat, self.lon = z["lat"], z["lon"]
        self.t0 = self.time[0]

    def cell_of(self, lat, lon):
        i = np.rint((lat - self.lat[0]) / 0.1).astype(int)
        j = np.rint((lon - self.lon[0]) / 0.1).astype(int)
        ok = (i >= 0) & (i < len(self.lat)) & (j >= 0) & (j < len(self.lon))
        return np.where(ok, i, -1), np.where(ok, j, -1)

    def day_index(self, dates):
        return (dates.astype("datetime64[D]") - self.t0).astype(int)


def hamon_pet(tg, lat_deg, doy):
    """Hamon (1961) potential evapotranspiration, mm/day."""
    decl = 0.4093 * np.sin(2 * np.pi * doy / 365.0 - 1.405)
    phi = np.deg2rad(lat_deg)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(decl), -1, 1))
    daylen = 24.0 * ws / np.pi
    es = 6.108 * np.exp(17.27 * tg / (tg + 237.3))
    rhosat = 216.7 * es / (tg + 273.3)
    return np.maximum(0.0, 0.1651 * (daylen / 12.0) * rhosat * 1.2)


def cell_series(w, cells):
    """Daily series (time, n_cells) for the requested cells, plus derived indices."""
    ii, jj = cells[:, 0], cells[:, 1]
    rr = np.nan_to_num(w.rr[:, ii, jj], nan=0.0)
    tg = w.tg[:, ii, jj]
    doy = (w.time - w.time.astype("datetime64[Y]")).astype(int) + 1
    pet = hamon_pet(np.nan_to_num(tg, nan=10.0), w.lat[ii][None, :], doy[:, None])
    swb = np.empty_like(rr)
    s = np.full(rr.shape[1], WMAX)
    for t in range(rr.shape[0]):   # simple bucket: AET proportional to relative storage
        s = np.clip(s + rr[t] - pet[t] * (s / WMAX), 0.0, WMAX)
        swb[t] = s / WMAX
    return rr, tg, swb


def features(w, cell_ids, cells, day_idx):
    rr, tg, swb = cell_series(w, cells)
    n = np.arange(len(cell_ids))
    cols = {}
    cs_r = np.vstack([np.zeros((1, rr.shape[1])), np.cumsum(rr, axis=0)])
    cs_t = np.vstack([np.zeros((1, tg.shape[1])), np.cumsum(np.nan_to_num(tg, nan=0.0), axis=0)])
    t1 = day_idx + 1   # cumulative arrays are shifted by one row
    for k in RAIN_WINDOWS:
        cols[f"P{k}"] = cs_r[t1, cell_ids] - cs_r[t1 - k, cell_ids]
    for a, b in LAGGED_RAIN:
        cols[f"P_{a}_{b}"] = cs_r[t1 - a, cell_ids] - cs_r[t1 - b, cell_ids]
    for k in TEMP_WINDOWS:
        cols[f"T{k}"] = (cs_t[t1, cell_ids] - cs_t[t1 - k, cell_ids]) / k
    cols["dT7"] = cols["T7"] - (cs_t[t1 - 7, cell_ids] - cs_t[t1 - 14, cell_ids]) / 7
    cols["SWB"] = swb[day_idx, cell_ids]
    cols["SWB_mean14"] = np.array([swb[max(0, d - 13): d + 1, c].mean() for d, c in zip(day_idx, cell_ids)])
    wet = rr >= 10.0
    since = []
    for d, c in zip(day_idx, cell_ids):
        win = wet[max(0, d - 59): d + 1, c]
        hits = np.flatnonzero(win)
        since.append(len(win) - 1 - hits[-1] if len(hits) else 60)
    cols["days_since_10mm"] = np.array(since)
    cols["rain_days14"] = np.array([(rr[max(0, d - 13): d + 1, c] >= 1.0).sum() for d, c in zip(day_idx, cell_ids)])
    return pd.DataFrame(cols, index=n)


# ------------------------------------------------------------ occurrences ----
def load_positives(w, csv_path):
    df = pd.read_csv(csv_path)
    df = df[df["day"].notna() & df["month"].notna() & (df["day"] != 1)]          # drop default-dated records
    df = df[df["eventDate"].astype(str).str.len() >= 10]
    df = df[~df["eventDate"].astype(str).str.contains("/")]                       # drop date ranges
    unc = df["coordinateUncertaintyInMeters"]
    df = df[unc.isna() | (unc <= 5000)]
    df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=df.day), errors="coerce")
    df = df[df["date"].notna()]
    i, j = w.cell_of(df["decimalLatitude"].to_numpy(), df["decimalLongitude"].to_numpy())
    df["i"], df["j"] = i, j
    df = df[(df.i >= 0) & (df.j >= 0)]
    df["t"] = w.day_index(df["date"].to_numpy())
    df = df[(df.t >= 70) & (df.t < len(w.time))]
    df = df[~np.isnan(w.tg[df.t.to_numpy(), df.i.to_numpy(), df.j.to_numpy()])]
    return df.drop_duplicates(["i", "j", "t"])


def build_dataset(w, pos, design, window=None):
    """design: 'same' = pseudo-absence dates in the positive's own year (within-season timing only);
    'matched' = years drawn from the positives' year distribution (adds between-year contrast)."""
    doy = pos["date"].dt.day_of_year.to_numpy()
    lo, hi = window or tuple(np.percentile(doy, [2.5, 97.5]).astype(int))
    pos = pos[(doy >= lo) & (doy <= hi)].copy()
    rows = [pd.DataFrame({"i": pos.i, "j": pos.j, "t": pos.t, "y": 1, "year": pos.date.dt.year})]
    reps = np.repeat(np.arange(len(pos)), K_PSEUDO)
    pos_years = pos.date.dt.year.to_numpy()
    ry = pos_years[reps] if design == "same" else RNG.choice(pos_years, size=len(reps))
    rd = RNG.integers(lo, hi + 1, size=len(reps))
    dates = pd.to_datetime([f"{a}-01-01" for a in ry]) + pd.to_timedelta(rd - 1, unit="D")
    t = w.day_index(dates.to_numpy())
    keep = (t >= 70) & (t < len(w.time))
    rows.append(pd.DataFrame({"i": pos.i.to_numpy()[reps][keep], "j": pos.j.to_numpy()[reps][keep],
                              "t": t[keep], "y": 0, "year": ry[keep]}))
    data = pd.concat(rows, ignore_index=True)
    data = data.drop_duplicates(["i", "j", "t"], keep="first").reset_index(drop=True)
    cells, cell_ids = np.unique(data[["i", "j"]].to_numpy(), axis=0, return_inverse=True)
    X = features(w, cell_ids.ravel(), cells, data.t.to_numpy())
    date = w.time[data.t.to_numpy()]
    d = (date - date.astype("datetime64[Y]")).astype(int) + 1
    X["doy_sin"], X["doy_cos"] = np.sin(2 * np.pi * d / 365.25), np.cos(2 * np.pi * d / 365.25)
    X["lat"], X["lon"] = w.lat[data.i.to_numpy()], w.lon[data.j.to_numpy()]
    data["block"] = (np.floor(X["lat"] / 2) * 100 + np.floor(X["lon"] / 2)).astype(int)
    return data, X, (int(lo), int(hi))


# ----------------------------------------------------------------- models ----
SEASON = ["doy_sin", "doy_cos", "lat", "lon"]


def model():
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=40, l2_regularization=1.0, random_state=0)


def cv_auc(X, y, groups):
    pred = np.full(len(y), np.nan)
    for g in np.unique(groups):
        te = groups == g
        if y[te].sum() < 5 or y[~te].sum() < 20:
            continue
        m = model().fit(X[~te], y[~te])
        pred[te] = m.predict_proba(X[te])[:, 1]
    ok = ~np.isnan(pred)
    return roc_auc_score(y[ok], pred[ok]), pred


def top_decile_lift(y, p):
    ok = ~np.isnan(p)
    y, p = y[ok], p[ok]
    thr = np.quantile(p, 0.9)
    return y[p >= thr].mean() / y.mean()


def run(eobs, gbif_dir, out_dir):
    w = Weather(eobs)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    jobs = [(sp, fr, d, None) for sp, fr in SPECIES.items() for d in ("matched", "same")]
    # Effort control: a tree is observed whatever the weather of the previous weeks; any "weather
    # signal" found for it measures observer behaviour, not biology. Uses the B. edulis season window.
    jobs += [("Fagus_sylvatica", "Témoin : hêtre (effort d'observation)", d, "Boletus_edulis") for d in ("matched", "same")]
    windows = {}
    for sp, fr, design, window_of in jobs:
        pos = load_positives(w, Path(gbif_dir) / f"{sp}.csv")
        data, X, (lo, hi) = build_dataset(w, pos, design, windows.get(window_of))
        windows.setdefault(sp, (lo, hi))
        y = data.y.to_numpy()
        weather_cols = [c for c in X.columns if c not in SEASON]
        res = {"species": sp, "nom": fr, "design": design, "n_pos": int(y.sum()), "n_pseudo": int((1 - y).sum()),
               "n_cells": int(data[data.y == 1][["i", "j"]].drop_duplicates().shape[0]),
               "season_doy": [lo, hi]}
        for name, cols in [("saison", SEASON), ("meteo", weather_cols), ("saison+meteo", SEASON + weather_cols)]:
            auc_y, p_y = cv_auc(X[cols].to_numpy(), y, data.year.to_numpy())
            auc_s, _ = cv_auc(X[cols].to_numpy(), y, data.block.to_numpy())
            res[f"auc_year_{name}"] = round(auc_y, 3)
            res[f"auc_block_{name}"] = round(auc_s, 3)
            res[f"lift10_{name}"] = round(top_decile_lift(y, p_y), 2)
        # univariate contrasts: median of key variables, positives vs pseudo-absences
        for c in ["P30", "P_14_21", "T14", "SWB", "dT7", "days_since_10mm"]:
            res[f"med_pos_{c}"] = round(float(np.median(X.loc[y == 1, c])), 2)
            res[f"med_bg_{c}"] = round(float(np.median(X.loc[y == 0, c])), 2)
        print(json.dumps(res, ensure_ascii=False), flush=True)
        summary.append(res)
        X.assign(y=y, year=data.year, i=data.i, j=data.j, t=data.t).to_csv(out / f"{sp}_{design}_dataset.csv.gz", index=False)
    pd.DataFrame(summary).to_csv(out / "summary.csv", index=False)


if __name__ == "__main__":
    run(*sys.argv[1:4])
