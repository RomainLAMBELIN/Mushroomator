"""Weather features shared by training (E-OBS) and daily inference (Open-Meteo).

All functions take daily series shaped (time, points) and return arrays of the same shape.
"""
import numpy as np

WMAX = 120.0     # bucket capacity (mm): typical available water of a forest soil
HISTORY_DAYS = 60  # longest look-back window used by any feature

# Every feature that can be fed to a model. Temperature features (prefix "T") depend on elevation and are
# exported reduced to sea level for the web application, which moves them to each pixel's elevation.
FEATURE_LABELS = {
    "doy": "Saison (jour de l'année)",
    "T3": "Température moyenne des 3 derniers jours",
    "T7": "Température moyenne des 7 derniers jours",
    "T14": "Température moyenne des 14 derniers jours",
    "T21": "Température moyenne des 21 derniers jours",
    "dT7": "Variation de température sur une semaine",
    "P3": "Pluie des 3 derniers jours",
    "P14": "Pluie des 14 derniers jours",
    "P30": "Pluie des 30 derniers jours",
    "P60": "Pluie des 60 derniers jours",
    "P_7_21": "Pluie tombée il y a 1 à 3 semaines",
    "SWB": "Réserve en eau du sol (bilan pluie − évaporation)",
}
FEATURE_UNITS = {"doy": "", "T3": "°C", "T7": "°C", "T14": "°C", "T21": "°C", "dT7": "°C", "P3": "mm",
                 "P14": "mm", "P30": "mm", "P60": "mm", "P_7_21": "mm", "SWB": "%"}


def is_temperature(name):
    return name.startswith("T")


def hamon_pet(tg, lat_deg, doy):
    """Hamon (1961) potential evapotranspiration (mm/day)."""
    decl = 0.4093 * np.sin(2 * np.pi * doy / 365.0 - 1.405)
    phi = np.deg2rad(lat_deg)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(decl), -1, 1))
    daylen = 24.0 * ws / np.pi
    es = 6.108 * np.exp(17.27 * tg / (tg + 237.3))
    rhosat = 216.7 * es / (tg + 273.3)
    return np.maximum(0.0, 0.1651 * (daylen / 12.0) * rhosat * 1.2)


def bucket(rr, pet, s0=None):
    """Relative soil-water storage (0-1) of a single-layer bucket; AET proportional to storage."""
    s = np.full(rr.shape[1], WMAX) if s0 is None else np.asarray(s0, dtype=float) * WMAX
    out = np.empty_like(rr, dtype=float)
    for t in range(rr.shape[0]):
        s = np.clip(s + rr[t] - pet[t] * (s / WMAX), 0.0, WMAX)
        out[t] = s / WMAX
    return out


def _trailing(cs, t_end, t_start):
    """Sum of the original series over days (t_start, t_end] from its cumulative sum `cs` (with a zero row)."""
    return cs[t_end + 1] - cs[t_start + 1]


def compute(rr, tg, doy, lat, swb0=None):
    """All features for every day; days with an incomplete history are NaN.

    rr, tg: (time, points) daily precipitation (mm) and mean temperature (°C)
    doy: (time,) day of year; lat: (points,) latitude in degrees; swb0: initial relative storage
    """
    rr = np.nan_to_num(np.asarray(rr, dtype=float), nan=0.0)
    tg = np.asarray(tg, dtype=float)
    n = rr.shape[0]
    t = np.arange(n)
    pet = hamon_pet(np.nan_to_num(tg, nan=10.0), np.asarray(lat)[None, :], np.asarray(doy)[:, None])
    swb = bucket(rr, pet, swb0)
    zero = np.zeros((1, rr.shape[1]))
    cs_r = np.vstack([zero, np.cumsum(rr, axis=0)])
    cs_t = np.vstack([zero, np.cumsum(np.nan_to_num(tg, nan=0.0), axis=0)])

    def rain(a, b):   # rain fallen from b-1 to a days before t (a=0: includes day t)
        return _trailing(cs_r, np.clip(t - a, -1, n - 1), np.clip(t - b, -1, n - 1))

    def temp(a, b):
        return _trailing(cs_t, np.clip(t - a, -1, n - 1), np.clip(t - b, -1, n - 1)) / (b - a)

    f = {
        "doy": np.repeat(np.asarray(doy, dtype=float)[:, None], rr.shape[1], axis=1),
        "T3": temp(0, 3), "T7": temp(0, 7), "T14": temp(0, 14), "T21": temp(0, 21),
        "P3": rain(0, 3), "P14": rain(0, 14), "P30": rain(0, 30), "P60": rain(0, 60), "P_7_21": rain(7, 21),
        "SWB": swb,
    }
    f["dT7"] = f["T7"] - temp(7, 14)
    incomplete = t < HISTORY_DAYS - 1
    for k in f:
        if k != "doy":
            f[k][incomplete] = np.nan
    return f
