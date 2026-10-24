"""Check the habitat layer against the region's observations.

Each species' records are compared with records of other common forest fungi (target group): both share the
observers' habits, so a good habitat layer must give higher suitability to the species' own records.
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import habitat, layers
from .config import ASSETS_DIR, LAPSE_RATE, REGIONS
from .hosts import HOST_GROUPS
from .sources import gbif

YEARS = (1990, 2026)
MAX_UNCERTAINTY_M = 500


def regional_records(names, region):
    frames = [gbif.occurrences(n, ("FR",), YEARS, bbox=region.bbox) for n in names]
    df = pd.concat(frames, ignore_index=True)
    unc = pd.to_numeric(df["coordinateUncertaintyInMeters"], errors="coerce")
    df = df[unc.isna() | (unc <= MAX_UNCERTAINTY_M)]
    return df.drop_duplicates(["decimalLatitude", "decimalLongitude", "scientificName"])


def pixel_values(L, df, array):
    r, c = L.grid.index_of(df.decimalLongitude.to_numpy(), df.decimalLatitude.to_numpy())
    ok = r >= 0
    return array[r[ok], c[ok]], ok


PSEUDO_COUNT = 5.0    # shrinks the observed host ratios towards 1 when a group holds few records
DATA_WEIGHT = 0.5     # geometric weight of the observed ratio against the expert prior
FOLDS = 5


def calibrated_hosts(prior, sp_groups, tg_groups):
    """Expert host table (codes 0..N) times the shrunk selection ratio of each group, rescaled to max 1."""
    n = len(prior)
    n_sp = np.bincount(sp_groups, minlength=n).astype(float)
    expected = np.bincount(tg_groups, minlength=n) / max(len(tg_groups), 1) * len(sp_groups)
    ratio = ((n_sp + PSEUDO_COUNT) / (expected + PSEUDO_COUNT)) ** DATA_WEIGHT
    table = prior * ratio
    table[0] = 0.0                                   # pixels without any forest formation stay empty
    return table / table.max() if table.max() > 0 else prior


def host_cross_validation(prior, sp_groups, h_rest_sp, tg_groups, h_rest_tg, seed=0):
    """Held-out AUC of the habitat with expert vs calibrated host tables (H = host × rest)."""
    rng = np.random.default_rng(seed)
    f_sp, f_tg = rng.integers(0, FOLDS, len(sp_groups)), rng.integers(0, FOLDS, len(tg_groups))
    scores = {"prior": [], "calibre": []}
    for k in range(FOLDS):
        table = calibrated_hosts(prior, sp_groups[f_sp != k], tg_groups[f_tg != k])
        te_sp, te_tg = f_sp == k, f_tg == k
        y = np.r_[np.ones(te_sp.sum()), np.zeros(te_tg.sum())]
        for name, t in (("prior", prior), ("calibre", table)):
            s = np.r_[t[sp_groups[te_sp]] * h_rest_sp[te_sp], t[tg_groups[te_tg]] * h_rest_tg[te_tg]]
            scores[name].append(roc_auc_score(y, s))
    return {k: round(float(np.mean(v)), 3) for k, v in scores.items()}


def run(region_key, log=print):
    region = REGIONS[region_key]
    L = layers.load(region_key)
    target = regional_records(gbif.TARGET_GROUP, region)
    log(f"Groupe cible : {len(target)} observations d'autres champignons forestiers")
    report = {"region": region_key, "target_group_records": int(len(target)),
              "method": {"pseudo_count": PSEUDO_COUNT, "data_weight": DATA_WEIGHT, "folds": FOLDS}, "species": {}}
    names = ["aucune"] + [k for k, _ in HOST_GROUPS]
    for key, spec in habitat.load_species().items():
        sp = regional_records(spec["gbif"], region)
        g_sp, _ = pixel_values(L, sp, L.host)
        g_tg, _ = pixel_values(L, target, L.host)
        rest = habitat.elevation_factor(L.elev, spec) * habitat.ph_factor(L.ph, spec)
        r_sp, _ = pixel_values(L, sp, rest)
        r_tg, _ = pixel_values(L, target, rest)
        prior = habitat.host_table(spec)
        cv = host_cross_validation(prior, g_sp, r_sp, g_tg, r_tg) if len(g_sp) >= 2 * FOLDS else None
        calibrated = calibrated_hosts(prior, g_sp, g_tg)
        use_calibrated = cv is not None and cv["calibre"] > cv["prior"]
        table = calibrated if use_calibrated else prior
        h_sp, h_tg = table[g_sp] * r_sp, table[g_tg] * r_tg
        share_sp = np.bincount(g_sp, minlength=len(names)) / max(len(g_sp), 1)
        share_tg = np.bincount(g_tg, minlength=len(names)) / max(len(g_tg), 1)
        ratios = {names[g]: round(float(share_sp[g] / share_tg[g]), 2)
                  for g in range(len(names)) if share_tg[g] > 0.005 and share_sp[g] > 0}
        e_sp, _ = pixel_values(L, sp, L.elev)
        res = {
            "records": int(len(g_sp)),
            "auc_validation_croisee": cv,
            "hotes_calibres_utilises": bool(use_calibrated),
            "hotes": {names[g]: round(float(table[g]), 3) for g in range(1, len(names))},
            "habitat_moyen": round(float(h_sp.mean()), 3) if len(h_sp) else None,
            "habitat_moyen_groupe_cible": round(float(h_tg.mean()), 3),
            "altitude_mediane": round(float(np.nanmedian(e_sp))) if np.isfinite(e_sp).any() else None,
            "rapports_de_selection_hotes": ratios,
        }
        report["species"][key] = res
        log(f"  {spec['nom']}: {res['records']} obs. ; AUC habitat (validation croisée) a priori "
            f"{cv and cv['prior']} → calibré {cv and cv['calibre']} ; tables {'calibrées' if use_calibrated else 'a priori'}")
    out = ASSETS_DIR / "validation" / f"{region_key}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    log(f"Rapport : {out}")
    return report



# ------------------------------------------------------------- hindcast ----
def coarse_history(region, eo):
    """Features of every day at each weather-grid point from E-OBS (temperatures reduced to sea level)."""
    from . import features as feat
    from .grid import weather_axes
    from .weather import EXPORTED, fill_invalid_points

    lons, lats = weather_axes(region)
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    la, lo = la.ravel(), lo.ravel()
    i, j = eo.cell_of(la, lo)
    i, j = np.clip(i, 0, len(eo.lat) - 1), np.clip(j, 0, len(eo.lon) - 1)
    rr, tg, elev = eo.rr[:, i, j].astype(float), eo.tg[:, i, j].astype(float), eo.elev[i, j].astype(float)
    fill_invalid_points(la, lo, np.isfinite(tg).all(axis=0) & np.isfinite(elev), rr, tg, elev)
    doy = (eo.time - eo.time.astype("datetime64[Y]")).astype(int) + 1
    f = feat.compute(rr, tg, doy, la)
    shape = (len(eo.time), len(lats), len(lons))
    out = {"lons": lons, "lats": lats, "time": eo.time}
    for name in EXPORTED:
        if feat.is_temperature(name):
            out[name + "_sl"] = (f[name] - LAPSE_RATE * elev[None, :]).reshape(shape)
        else:
            out[name] = f[name].reshape(shape)
    return out


def index_at(sp, L, H, hist, lat, lon, t):
    """Habitat and conditions percentile of the published model at given places and days (forest pixels only)."""
    from . import predict
    from .features import HISTORY_DAYS
    from .grid import interp_weights

    lat, lon, t = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float), np.asarray(t, dtype=int)
    r, c = L.grid.index_of(lon, lat)
    keep = (r >= 0) & (t >= HISTORY_DAYS - 1) & (t < len(hist["time"]))
    keep[keep] &= L.host[r[keep], c[keep]] > 0
    r, c, t, lat, lon = r[keep], c[keep], t[keep], lat[keep], lon[keep]
    ix, fx = interp_weights(hist["lons"], lon)
    iy, fy = interp_weights(hist["lats"], lat)

    def interp(field):
        top = field[t, iy, ix] * (1 - fx) + field[t, iy, ix + 1] * fx
        bottom = field[t, iy + 1, ix] * (1 - fx) + field[t, iy + 1, ix + 1] * fx
        return top * (1 - fy) + bottom * fy

    m = sp["modele"]
    when = hist["time"][t]
    logit = m["intercept"] + predict.table(m["tables"]["doy"], (when - when.astype("datetime64[Y]")).astype(int) + 1)
    for f in m["features"]:
        if f == "doy":
            continue
        if predict.is_temperature(f):
            temp = interp(hist[f + "_sl"]) + LAPSE_RATE * np.nan_to_num(L.elev[r, c])
            logit = logit + predict.table(m["tables"][f], temp)
        else:
            logit = logit + interp(predict.table(m["tables"][f], hist[f]))
    return H[r, c], predict.percentile(m["quantiles"], logit)


def hindcast(region_key, log=print):
    """End-to-end check of the published index on past seasons (E-OBS replay, 2011 to mid-2024).

    - same places, other days: are observation days rated higher than random days of the same year?
    - index vs other fungi: are the species' records rated higher than other forest fungi's records?
    """
    from . import predict, site
    from .sources import eobs

    region = REGIONS[region_key]
    L = layers.load(region_key)
    eo = eobs.load(log)
    hist = coarse_history(region, eo)
    rng = np.random.default_rng(1)
    target = gbif.clean(regional_records(gbif.TARGET_GROUP, region))
    tg_t = eo.day_index(target.date.values)
    report = {}
    for sp in site.species_payload(region_key):
        names = habitat.load_species()[sp["key"]]["gbif"]
        obs = gbif.clean(regional_records(names, region))
        H = predict.habitat(sp, L)
        lat, lon, t = obs.decimalLatitude.to_numpy(), obs.decimalLongitude.to_numpy(), eo.day_index(obs.date.values)
        h1, q1 = index_at(sp, L, H, hist, lat, lon, t)
        if len(q1) < 20:
            continue
        reps = np.repeat(np.arange(len(obs)), 5)
        jan1 = eo.day_index(obs.date.dt.year.to_numpy()[reps].astype(str).astype("datetime64[Y]").astype("datetime64[D]"))
        h0, q0 = index_at(sp, L, H, hist, lat[reps], lon[reps], jan1 + rng.integers(0, 365, len(reps)))
        hg, qg = index_at(sp, L, H, hist, target.decimalLatitude.to_numpy(), target.decimalLongitude.to_numpy(), tg_t)
        auc_days = roc_auc_score(np.r_[np.ones(len(q1)), np.zeros(len(q0))], np.r_[q1, q0])
        auc_fungi = roc_auc_score(np.r_[np.ones(len(q1)), np.zeros(len(qg))], np.r_[h1 * q1, hg * qg])
        report[sp["key"]] = {
            "observations": int(len(q1)),
            "auc_meme_lieu_autres_jours": round(float(auc_days), 3),
            "auc_indice_vs_autres_champignons": round(float(auc_fungi), 3),
            "indice_median_observations": round(float(np.median(h1 * q1)), 3),
            "indice_median_autres_champignons": round(float(np.median(hg * qg)), 3),
        }
        log(f"  {sp['nom']}: {len(q1)} obs. ; AUC même lieu/autres jours {auc_days:.3f} ; "
            f"AUC indice vs autres champignons {auc_fungi:.3f}")
    out = ASSETS_DIR / "validation" / f"{region_key}.json"
    full = json.loads(out.read_text()) if out.exists() else {"region": region_key, "species": {}}
    full["hindcast"] = {"period": [str(eo.time[0]), str(eo.time[-1])], "species": report}
    out.write_text(json.dumps(full, ensure_ascii=False, indent=1))
    return report
