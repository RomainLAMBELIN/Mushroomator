"""Copernicus DEM GLO-90 → mean elevation per grid pixel.

Data: Copernicus DEM © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under
COPERNICUS by the European Union and ESA; open public AWS bucket.
"""
import math
from pathlib import Path

import numpy as np

from .. import net
from ..config import DATA_DIR

URL = ("https://copernicus-dem-90m.s3.amazonaws.com/Copernicus_DSM_COG_30_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
       "Copernicus_DSM_COG_30_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif")


def tiles(west, south, east, north):
    for lat in range(math.floor(south), math.ceil(north)):
        for lon in range(math.floor(west), math.ceil(east)):
            yield URL.format(ns="N" if lat >= 0 else "S", lat=abs(lat), ew="E" if lon >= 0 else "W", lon=abs(lon))


def _tile_overview(url, cache_dir):
    """Elevation array of a tile's 1/4 overview (~360 m) and its transform, cached as .npz."""
    import rasterio

    cache = Path(cache_dir) / (url.rsplit("/", 1)[1].replace(".tif", "_ov4.npz"))
    if cache.exists():
        z = np.load(cache)
        return z["elev"], tuple(z["transform"])
    try:
        with rasterio.open("/vsicurl/" + url, overview_level=1) as src:
            elev, transform = src.read(1).astype(np.float32), tuple(src.transform)[:6]
    except rasterio.errors.RasterioIOError:   # no tile: open sea
        elev, transform = np.zeros((1, 1), np.float32), (1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, elev=elev, transform=np.array(transform))
    return elev, transform


def sample_points(lat, lon):
    """Ground elevation (m) of points from Copernicus DEM overviews (~360 m), downloading only needed tiles."""
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
    out = np.full(lat.shape, np.nan)
    tile_lat, tile_lon = np.floor(lat).astype(int), np.floor(lon).astype(int)
    for la, lo in sorted(set(zip(tile_lat.tolist(), tile_lon.tolist()))):
        url = next(tiles(lo, la, lo + 1, la + 1))
        elev, (a, _, c, _, e, f) = _tile_overview(url, DATA_DIR / "raw" / "dem_overviews")
        sel = (tile_lat == la) & (tile_lon == lo)
        col = np.clip(((lon[sel] - c) / a).astype(int), 0, elev.shape[1] - 1)
        row = np.clip(((lat[sel] - f) / e).astype(int), 0, elev.shape[0] - 1)
        out[sel] = elev[row, col]
    return out


def build(grid, region, log=print):
    """Elevation (m, float32) on `grid`; NaN where no DEM tile exists (open sea)."""
    import rasterio
    from rasterio.merge import merge
    from rasterio.warp import Resampling, reproject

    raw = Path(DATA_DIR / "raw" / "dem")
    paths = []
    for url in tiles(*region.bbox):
        try:
            paths.append(net.download(url, raw / url.rsplit("/", 1)[1]))
        except Exception as e:  # noqa: BLE001 - missing tiles (sea) are expected
            log(f"  MNT : tuile absente {url.rsplit('/', 1)[1]} ({e})")
    sources = [rasterio.open(p) for p in paths]
    try:
        mosaic, transform = merge(sources, nodata=-32768)
        crs = sources[0].crs
    finally:
        for s in sources:
            s.close()
    out = np.full(grid.shape, np.nan, dtype=np.float32)
    reproject(mosaic[0].astype(np.float32), out, src_transform=transform, src_crs=crs, src_nodata=-32768,
              dst_transform=grid.transform, dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.average)
    log(f"  MNT : {len(paths)} tuiles, altitude {np.nanmin(out):.0f}–{np.nanmax(out):.0f} m")
    return out
