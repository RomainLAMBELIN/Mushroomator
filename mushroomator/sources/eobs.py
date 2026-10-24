"""E-OBS daily gridded observations, used only to train the weather-trigger models.

Licence: E-OBS is restricted to non-commercial research and education (Cornes et al. 2018,
https://doi.org/10.1029/2017JD028200; ECA&D project). Mushroomator is a personal, non-commercial project.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .. import net
from ..config import DATA_DIR

BASE = "https://knmi-ecad-assets-prd.s3.amazonaws.com/ensembles/data/Grid_0.1deg_reg_ensemble"
VERSION = "v30.0e"
FILES = {"rr": f"rr_ens_mean_0.1deg_reg_2011-2024_{VERSION}.nc", "tg": f"tg_ens_mean_0.1deg_reg_2011-2024_{VERSION}.nc",
         "elev": f"elev_ens_0.1deg_reg_{VERSION}.nc"}
LON, LAT = (-5.5, 10.5), (41.0, 51.5)   # France, Switzerland and borders


@dataclass
class EObs:
    rr: np.ndarray      # (time, lat, lon) mm/day
    tg: np.ndarray      # (time, lat, lon) °C
    elev: np.ndarray    # (lat, lon) m
    time: np.ndarray    # datetime64[D]
    lat: np.ndarray
    lon: np.ndarray

    def cell_of(self, lat, lon):
        i = np.rint((np.asarray(lat) - self.lat[0]) / 0.1).astype(int)
        j = np.rint((np.asarray(lon) - self.lon[0]) / 0.1).astype(int)
        ok = (i >= 0) & (i < len(self.lat)) & (j >= 0) & (j < len(self.lon))
        return np.where(ok, i, -1), np.where(ok, j, -1)

    def day_index(self, dates):
        return (np.asarray(dates).astype("datetime64[D]") - self.time[0]).astype(int)


def load(log=print):
    cache = Path(DATA_DIR / "eobs" / f"eobs_{VERSION}_fr-ch.npz")
    if not cache.exists():
        import xarray as xr
        raw = Path(DATA_DIR / "raw" / "eobs")
        paths = {k: net.download(f"{BASE}/{f}", raw / f) for k, f in FILES.items()}
        sub = {}
        for var in ("rr", "tg"):
            log(f"  extraction E-OBS {var}…")
            da = xr.open_dataset(paths[var], engine="netcdf4")[var].sel(longitude=slice(*LON), latitude=slice(*LAT))
            sub[var] = da.astype("float32").load()
        elev = xr.open_dataset(paths["elev"], engine="netcdf4")["elevation"].sel(longitude=slice(*LON), latitude=slice(*LAT))
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, rr=sub["rr"].values, tg=sub["tg"].values, elev=elev.values.astype("float32"),
                            time=sub["rr"].time.values.astype("datetime64[D]"),
                            lat=sub["rr"].latitude.values, lon=sub["rr"].longitude.values)
    z = np.load(cache)
    return EObs(z["rr"], z["tg"], z["elev"], z["time"].astype("datetime64[D]"), z["lat"], z["lon"])
