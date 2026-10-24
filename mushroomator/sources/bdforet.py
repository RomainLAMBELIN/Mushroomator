"""IGN BD Forêt V2 → raster of host groups on the region grid.

Data: IGN, BD Forêt® V2 (Licence Ouverte Etalab 2.0), one 7z archive of shapefiles per département.
"""
import re
from pathlib import Path

import numpy as np

from .. import net
from ..config import DATA_DIR
from ..hosts import HOST_GROUPS, group_of_tfv

FEED = "https://data.geopf.fr/telechargement/resource/BDFORET"
FINE_FACTOR = 5          # rasterise at pixel/5, then take the dominant group of each pixel
MIN_FOREST_SHARE = 0.2   # a pixel counts as forest when at least 20 % of it is covered


def archive_url(dept):
    zone = f"D{int(dept):03d}" if dept.isdigit() else f"D{dept}"
    feed = net.get(FEED, params={"zone": zone}).text
    names = sorted(set(re.findall(rf"BDFORET_2-0__SHP_LAMB93_{zone}_[0-9-]+", feed)))
    if not names:
        raise RuntimeError(f"BD Forêt V2 introuvable pour le département {dept}")
    name = names[-1]   # most recent edition
    return f"{FEED.replace('/resource/', '/download/')}/{name}/{name}.7z"


def fetch(dept, raw_dir=None):
    """Download and extract the département archive; return the FORMATION_VEGETALE shapefile path."""
    import py7zr
    raw_dir = Path(raw_dir or DATA_DIR / "raw" / "bdforet")
    out = raw_dir / f"D{dept}"
    found = list(out.glob("**/FORMATION_VEGETALE.shp"))
    if found:
        return found[0]
    archive = net.download(archive_url(dept), raw_dir / f"D{dept}.7z")
    with py7zr.SevenZipFile(archive) as z:
        wanted = [n for n in z.getnames() if "/FORMATION_VEGETALE." in n]
        z.extract(out, targets=wanted)
    return next(out.glob("**/FORMATION_VEGETALE.shp"))


def read_groups(shp, bbox_3857=None):
    """Geometries (EPSG:3857, shapely) and host-group codes of a BD Forêt shapefile."""
    import pyogrio.raw as raw
    import shapely
    from pyproj import Transformer

    meta, _, wkb, fields = raw.read(shp, columns=["CODE_TFV"])
    codes = np.array([group_of_tfv(c) for c in fields[0]], dtype=np.uint8)
    geoms = shapely.from_wkb(wkb)
    to_merc = Transformer.from_crs(meta["crs"], "EPSG:3857", always_xy=True)
    geoms = shapely.transform(geoms, lambda xy: np.column_stack(to_merc.transform(xy[:, 0], xy[:, 1])))
    keep = codes > 0
    if bbox_3857 is not None:
        keep &= shapely.intersects(geoms, shapely.box(*bbox_3857))
    return geoms[keep], codes[keep]


def build(grid, departments, log=print):
    """Dominant host group (uint8, 0 = none) and forest share (0-100 %) per grid pixel."""
    from rasterio.features import rasterize

    fine = grid.refine(FINE_FACTOR)
    bbox = (grid.x0, grid.y1 - grid.ny * grid.res, grid.x0 + grid.nx * grid.res, grid.y1)
    canvas = np.zeros(fine.shape, dtype=np.uint8)
    for dept in departments:
        geoms, codes = read_groups(fetch(dept), bbox)
        log(f"  BD Forêt D{dept}: {len(geoms)} formations")
        if len(geoms):
            rasterize(zip(geoms, codes), out=canvas, transform=fine.transform)
    f = FINE_FACTOR
    blocks = canvas.reshape(grid.ny, f, grid.nx, f)
    counts = np.stack([(blocks == g).sum(axis=(1, 3), dtype=np.uint16) for g in range(1, len(HOST_GROUPS) + 1)])
    covered = counts.sum(axis=0)
    dominant = (counts.argmax(axis=0) + 1).astype(np.uint8)
    dominant[covered < MIN_FOREST_SHARE * f * f] = 0
    share = np.round(100.0 * covered / (f * f)).astype(np.uint8)
    return dominant, share
