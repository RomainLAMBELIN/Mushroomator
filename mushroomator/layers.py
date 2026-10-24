"""Static layers of a region (host group, forest share, elevation, pH), stored as gzipped binary rasters.

The same files are read by the Python pipeline and by the web application.
"""
import gzip
import json
from dataclasses import dataclass

import numpy as np

from .config import ASSETS_DIR, REGIONS
from .grid import Grid

FILES = {  # name -> (file, dtype, nodata)
    "host": ("host.u8.gz", "uint8", 0),
    "forest": ("forest.u8.gz", "uint8", 0),
    "elev": ("elev.u16.gz", "uint16", 65535),
    "ph10": ("ph10.u8.gz", "uint8", 0),
}
ATTRIBUTION = ("Forêts : IGN BD Forêt® V2 (Licence Ouverte) · Relief : Copernicus DEM GLO-90 · "
               "Sols : ISRIC SoilGrids 2.0 (CC-BY 4.0)")


def region_dir(region_key):
    return ASSETS_DIR / "regions" / region_key


@dataclass
class Layers:
    grid: Grid
    host: np.ndarray     # dominant host group (0 = none)
    forest: np.ndarray   # forest share of the pixel (%)
    elev: np.ndarray     # elevation (m, float, NaN = unknown)
    ph: np.ndarray       # topsoil pH (float, NaN = unknown)


def save(region, grid, host, forest, elev, ph):
    out = region_dir(region.key)
    out.mkdir(parents=True, exist_ok=True)
    # 10 m steps: negligible for temperature (0.07 °C) and halves the file size.
    elev_u16 = np.where(np.isfinite(elev), np.clip(np.round(elev / 10) * 10, 0, 65530), 65535).astype("<u2")
    ph10 = np.where(np.isfinite(ph), np.clip(np.round(ph * 10), 1, 255), 0).astype(np.uint8)
    arrays = {"host": host.astype(np.uint8), "forest": forest.astype(np.uint8), "elev": elev_u16, "ph10": ph10}
    for name, (fname, _, _) in FILES.items():
        (out / fname).write_bytes(gzip.compress(arrays[name].tobytes(order="C"), compresslevel=9, mtime=0))
    meta = {"region": region.key, "name": region.name, "grid": grid.to_dict(), "attribution": ATTRIBUTION,
            "files": {k: {"file": f, "dtype": d, "nodata": n} for k, (f, d, n) in FILES.items()}}
    (out / "layers.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return out


def load(region_key):
    d = region_dir(region_key)
    meta = json.loads((d / "layers.json").read_text())
    g = meta["grid"]
    grid = Grid(g["x0"], g["y1"], g["res"], g["nx"], g["ny"])
    arr = {}
    for name, info in meta["files"].items():
        raw = np.frombuffer(gzip.decompress((d / info["file"]).read_bytes()), dtype=np.dtype(info["dtype"]).newbyteorder("<"))
        arr[name] = raw.reshape(grid.shape)
    elev = np.where(arr["elev"] == 65535, np.nan, arr["elev"].astype(np.float32))
    ph = np.where(arr["ph10"] == 0, np.nan, arr["ph10"] / 10.0).astype(np.float32)
    return Layers(grid, arr["host"], arr["forest"], elev, ph)


def build(region_key, log=print):
    from .sources import bdforet, dem, soilgrids

    region = REGIONS[region_key]
    grid = Grid.from_region(region)
    log(f"Grille {grid.nx} x {grid.ny} pixels de {grid.res:.0f} m (Web Mercator)")
    elev = dem.build(grid, region, log)
    ph = soilgrids.build(grid, log)
    host, forest = bdforet.build(grid, region.departments, log)
    out = save(region, grid, host, forest, elev, ph)
    log(f"Couches enregistrées dans {out}")
    return out
