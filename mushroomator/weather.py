"""Daily weather on the coarse grid (Open-Meteo: 92 past days + 8-day forecast) and features for the web app.

Data: Open-Meteo.com (CC-BY 4.0), free API for non-commercial use. Temperatures are exported reduced to sea
level so that the application can move them to each pixel's elevation.
"""
import datetime as dt
import gzip
import json
import math
import time
from pathlib import Path

import numpy as np

from . import features as feat
from . import net
from .config import ASSETS_DIR, DATA_DIR, LAPSE_RATE
from .grid import weather_axes

API = "https://api.open-meteo.com/v1/forecast"
PAST_DAYS, FORECAST_DAYS = 92, 8
SHOW_PAST, SHOW_FUTURE = 7, 7          # days offered by the application around today
BATCH = 25                             # locations per request
MAX_CALLS_PER_MINUTE = 450             # free tier: 600 (a location with 100 days counts ~7 calls)
EXPORTED = ("T14", "P30", "P_7_21", "SWB")
TIMEZONE = "Europe/Paris"


def today_paris():
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo(TIMEZONE)).date()


def _fill_gaps(a):
    """Linear interpolation of missing days, per point."""
    a = np.array(a, dtype=float)
    t = np.arange(a.shape[0])
    for p in range(a.shape[1]):
        bad = ~np.isfinite(a[:, p])
        if bad.any() and (~bad).sum() >= 2:
            a[bad, p] = np.interp(t[bad], t[~bad], a[~bad, p])
    return a


def fetch(region, day=None, force=False, log=print):
    """Raw daily series for every point of the weather grid (cached per day)."""
    day = day or today_paris()
    cache = Path(DATA_DIR / "weather" / region.key / f"openmeteo_{day.isoformat()}.json.gz")
    if cache.exists() and not force:
        return json.loads(gzip.decompress(cache.read_bytes()))
    lons, lats = weather_axes(region)
    points = [(float(la), float(lo)) for la in lats for lo in lons]
    # explicit dates: every batch covers the same days, even when the download runs across midnight
    start = day - dt.timedelta(days=PAST_DAYS)
    dates = [(start + dt.timedelta(days=k)).isoformat() for k in range(PAST_DAYS + FORECAST_DAYS)]
    calls_per_request = BATCH * math.ceil((PAST_DAYS + FORECAST_DAYS) / 14)
    pause = 60.0 * calls_per_request / MAX_CALLS_PER_MINUTE
    results = []
    for k in range(0, len(points), BATCH):
        chunk = points[k:k + BATCH]
        params = {"latitude": ",".join(f"{p[0]:.4f}" for p in chunk), "longitude": ",".join(f"{p[1]:.4f}" for p in chunk),
                  "daily": "precipitation_sum,temperature_2m_mean,temperature_2m_max",
                  "start_date": dates[0], "end_date": dates[-1], "timezone": TIMEZONE}
        d = net.get_json(API, params=params)
        batch = d if isinstance(d, list) else [d]
        if any(r["daily"]["time"] != dates for r in batch):
            raise RuntimeError(f"Open-Meteo : jours inattendus dans la réponse (attendu {dates[0]} → {dates[-1]})")
        results += batch
        log(f"  météo : {len(results)}/{len(points)} points")
        if k + BATCH < len(points):
            time.sleep(pause)
    raw = {"day": day.isoformat(), "lons": lons.tolist(), "lats": lats.tolist(),
           "dates": dates,
           "elev": [r["elevation"] for r in results],
           "rr": [r["daily"]["precipitation_sum"] for r in results],
           "tg": [r["daily"]["temperature_2m_mean"] for r in results],
           "tx": [r["daily"]["temperature_2m_max"] for r in results]}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(gzip.compress(json.dumps(raw).encode(), mtime=0))
    return raw


def fill_invalid_points(lat, lon, valid, rr, tg, elev):
    """In place: points without data (lakes, sea) take the series of the nearest valid point."""
    good = np.flatnonzero(valid)
    for p in np.flatnonzero(~valid):
        k = good[np.argmin((lat[good] - lat[p]) ** 2 + (lon[good] - lon[p]) ** 2)]
        rr[:, p], tg[:, p], elev[p] = rr[:, k], tg[:, k], elev[k]


def replay_eobs(region, day, eo):
    """Same structure as `fetch`, built from E-OBS observations of a past date (the 'forecast' days are the
    observed weather). Used to replay known seasons and to test without network quota."""
    lons, lats = weather_axes(region)
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    la, lo = la.ravel(), lo.ravel()
    t0 = int(eo.day_index(np.datetime64(day)))
    if t0 - PAST_DAYS < 0 or t0 + FORECAST_DAYS > len(eo.time):
        raise ValueError(f"E-OBS couvre {eo.time[0]} → {eo.time[-1]} : impossible de rejouer le {day}")
    window = slice(t0 - PAST_DAYS, t0 + FORECAST_DAYS)
    i, j = eo.cell_of(la, lo)
    i, j = np.clip(i, 0, len(eo.lat) - 1), np.clip(j, 0, len(eo.lon) - 1)
    rr, tg, elev = eo.rr[window][:, i, j], eo.tg[window][:, i, j], eo.elev[i, j].astype(float)
    fill_invalid_points(la, lo, np.isfinite(tg).all(axis=0) & np.isfinite(elev), rr, tg, elev)
    return {"day": str(day), "lons": lons.tolist(), "lats": lats.tolist(),
            "dates": [str(d) for d in eo.time[window]], "elev": elev.tolist(),
            "rr": rr.T.tolist(), "tg": tg.T.tolist(), "tx": None,
            "source": "Rejeu E-OBS v30.0e (observations ; « prévisions » = météo réellement observée)"}


def swb_climatology_path(region):
    return ASSETS_DIR / "regions" / region.key / "swb_climatology.json"


def build_swb_climatology(region, eo, log=print):
    """Monthly mean soil-water index at each weather-grid point (E-OBS 2011-2023), used as initial state."""
    lons, lats = weather_axes(region)
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    i, j = eo.cell_of(la.ravel(), lo.ravel())
    i, j = np.clip(i, 0, len(eo.lat) - 1), np.clip(j, 0, len(eo.lon) - 1)
    rr, tg = eo.rr[:, i, j], eo.tg[:, i, j]
    tg = np.where(np.isfinite(tg), tg, np.nanmean(tg, axis=0))   # sea cells: any finite value
    doy = (eo.time - eo.time.astype("datetime64[Y]")).astype(int) + 1
    swb = feat.bucket(np.nan_to_num(rr), feat.hamon_pet(tg, la.ravel()[None, :], doy[:, None]))
    month = eo.time.astype("datetime64[M]").astype(int) % 12
    keep = eo.time >= np.datetime64("2012-01-01")             # one year of spin-up
    clim = np.stack([swb[keep & (month == m)].mean(axis=0) for m in range(12)]).reshape(12, len(lats), len(lons))
    path = swb_climatology_path(region)
    path.write_text(json.dumps({"lons": lons.tolist(), "lats": lats.tolist(), "monthly": np.round(clim, 3).tolist()}))
    log(f"  climatologie de la réserve en eau : {path}")
    return path


def export(region, raw, log=print):
    """Features of the days shown by the application, plus raw series for the charts."""
    lons, lats = np.array(raw["lons"]), np.array(raw["lats"])
    dates = np.array(raw["dates"], dtype="datetime64[D]")
    rr = _fill_gaps(np.array(raw["rr"], dtype=float).T)     # (time, points)
    tg = _fill_gaps(np.array(raw["tg"], dtype=float).T)
    tx = _fill_gaps(np.array(raw["tx"], dtype=float).T) if raw.get("tx") else None
    elev = np.array(raw["elev"], dtype=float)
    lat_pts = np.repeat(lats, len(lons))
    doy = (dates - dates.astype("datetime64[Y]")).astype(int) + 1
    swb0 = None
    clim_path = swb_climatology_path(region)
    if clim_path.exists():
        clim = np.array(json.loads(clim_path.read_text())["monthly"])
        swb0 = clim[int(str(dates[0])[5:7]) - 1].ravel()
    f = feat.compute(rr, tg, doy, lat_pts, swb0)
    day = np.datetime64(raw["day"])
    t0 = int(np.searchsorted(dates, day))
    show = np.arange(max(t0 - SHOW_PAST, feat.HISTORY_DAYS - 1), min(t0 + SHOW_FUTURE + 1, len(dates)))
    shape = (len(show), len(lats), len(lons))
    out = {}
    for name in EXPORTED:
        v = f[name][show]
        if feat.is_temperature(name):
            v = v - LAPSE_RATE * elev[None, :]                # reduce to sea level
            out[name + "_sl"] = np.round(v, 2).reshape(shape).tolist()
        else:
            out[name] = np.round(v, 3 if name == "SWB" else 1).reshape(shape).tolist()
    series_from = max(0, t0 - 45)
    return {
        "region": region.key, "today": raw["day"],
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
        "source": raw.get("source", "Open-Meteo.com (CC-BY 4.0) : 92 jours d'historique et prévision à 8 jours"),
        "lapse_rate": LAPSE_RATE,
        "lons": lons.tolist(), "lats": lats.tolist(),
        "elev": np.round(elev).reshape(len(lats), len(lons)).tolist(),
        "dates": [str(d) for d in dates[show]],
        "features": out,
        "series": {"dates": [str(d) for d in dates[series_from:]],
                   "rr": np.round(rr[series_from:].T, 1).tolist(),
                   "tg": np.round(tg[series_from:].T, 1).tolist(),
                   "tx": None if tx is None else np.round(tx[series_from:].T, 1).tolist()},
    }
