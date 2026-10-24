"""Index on the region grid from the site payloads (mirror of web/model.js, used by tests and statistics)."""
import datetime as dt

import numpy as np

from .config import LAPSE_RATE
from .grid import bilinear, interp_weights


def is_temperature(name):
    return name.startswith("T") and name != "dT7"


def day_of_year(iso):
    return dt.date.fromisoformat(iso).timetuple().tm_yday


def table(tab, x):
    return np.interp(x, tab["x"], tab["y"])


def percentile(quantiles, v):
    return np.interp(v, quantiles, np.linspace(0, 1, len(quantiles)))


def habitat(sp, layers):
    host = np.asarray(sp["hotes"], dtype=float)[layers.host]
    z0, z1, z2, z3 = sp["altitude"]
    z = layers.elev
    up = np.clip((z - z0) / max(z1 - z0, 1), 0, 1)
    down = np.clip((z3 - z) / max(z3 - z2, 1), 0, 1)
    floor = sp["altitude_plancher"]
    elev_f = np.where(np.isfinite(z), floor + (1 - floor) * np.minimum(up, down), 0.0)
    a, b = sp["ph"]
    ph_f = sp["ph_bas"] + (1 - sp["ph_bas"]) * np.clip((layers.ph - a) / (b - a), 0, 1)
    ph_f = np.where(np.isfinite(layers.ph), ph_f, 1.0)
    return host * elev_f * ph_f


def coarse_fields(sp, weather, day):
    m = sp["modele"]
    base = np.full((len(weather["lats"]), len(weather["lons"])),
                   m["intercept"] + table(m["tables"]["doy"], day_of_year(weather["dates"][day])))
    temps = {}
    for f in m["features"]:
        if f == "doy":
            continue
        if is_temperature(f):
            temps[f] = np.asarray(weather["features"][f + "_sl"][day], dtype=float)
        else:
            base = base + table(m["tables"][f], np.asarray(weather["features"][f][day], dtype=float))
    return base, temps


def conditions(sp, layers, weather, day):
    """Percentile (0-1) of the day's conditions at every pixel."""
    base, temps = coarse_fields(sp, weather, day)
    lon_w = interp_weights(np.asarray(weather["lons"]), layers.grid.column_lon())
    lat_w = interp_weights(np.asarray(weather["lats"]), layers.grid.row_lat())
    logit = bilinear(base, lon_w, lat_w)
    z = np.nan_to_num(layers.elev)
    for f, t in temps.items():
        logit = logit + table(sp["modele"]["tables"][f], bilinear(t, lon_w, lat_w) + LAPSE_RATE * z)
    return percentile(sp["modele"]["quantiles"], logit)


def index(sp, layers, weather, day):
    H = habitat(sp, layers)
    q = conditions(sp, layers, weather, day)
    out = H * q
    out[layers.host == 0] = np.nan
    return out
