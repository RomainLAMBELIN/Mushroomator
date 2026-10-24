"""Subset E-OBS daily grids to metropolitan France and store them as compact .npz.

Usage: python eobs_subset.py EOBS_DIR OUT_NPZ
"""
import sys
import numpy as np
import xarray as xr

LON = (-5.5, 10.0)
LAT = (41.0, 51.5)


def load(path, var):
    ds = xr.open_dataset(path, engine="netcdf4")
    da = ds[var].sel(longitude=slice(*LON), latitude=slice(*LAT))
    return da.astype("float32").load()


def main(eobs_dir, out):
    rr = load(f"{eobs_dir}/rr_ens_mean_0.1deg_reg_2011-2024_v30.0e.nc", "rr")
    tg = load(f"{eobs_dir}/tg_ens_mean_0.1deg_reg_2011-2024_v30.0e.nc", "tg")
    assert (rr.time.values == tg.time.values).all()
    np.savez_compressed(out, rr=rr.values, tg=tg.values, time=rr.time.values.astype("datetime64[D]"),
                        lat=rr.latitude.values, lon=rr.longitude.values)
    print(rr.shape, float(np.isnan(rr.values).mean()), float(np.isnan(tg.values).mean()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
