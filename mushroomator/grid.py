"""Web Mercator raster grid of a region (pixels map 1:1 onto a Leaflet image overlay)."""
import math
from dataclasses import dataclass

import numpy as np

R_EARTH = 6378137.0


def lonlat_to_merc(lon, lat):
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    return R_EARTH * np.radians(lon), R_EARTH * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))


def merc_to_lonlat(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    return np.degrees(x / R_EARTH), np.degrees(2 * np.arctan(np.exp(y / R_EARTH)) - np.pi / 2)


@dataclass(frozen=True)
class Grid:
    x0: float     # left edge (EPSG:3857, m)
    y1: float     # top edge
    res: float    # pixel size (m)
    nx: int
    ny: int

    @classmethod
    def from_region(cls, region, res=None):
        res = res or region.pixel_m
        (x0, y0), (x1, y1) = (lonlat_to_merc(region.west, region.south), lonlat_to_merc(region.east, region.north))
        x0, y0 = math.floor(float(x0) / res) * res, math.floor(float(y0) / res) * res
        x1, y1 = math.ceil(float(x1) / res) * res, math.ceil(float(y1) / res) * res
        return cls(x0, y1, res, int(round((x1 - x0) / res)), int(round((y1 - y0) / res)))

    def refine(self, factor):
        """Same extent with pixels `factor` times smaller (used for fine rasterisation)."""
        return Grid(self.x0, self.y1, self.res / factor, self.nx * factor, self.ny * factor)

    @property
    def transform(self):
        from affine import Affine
        return Affine(self.res, 0.0, self.x0, 0.0, -self.res, self.y1)

    @property
    def shape(self):
        return (self.ny, self.nx)

    def column_lon(self):
        return merc_to_lonlat(self.x0 + (np.arange(self.nx) + 0.5) * self.res, 0.0)[0]

    def row_lat(self):
        return merc_to_lonlat(0.0, self.y1 - (np.arange(self.ny) + 0.5) * self.res)[1]

    def bounds_lonlat(self):
        """(west, south, east, north) of the pixel edges."""
        w, n = merc_to_lonlat(self.x0, self.y1)
        e, s = merc_to_lonlat(self.x0 + self.nx * self.res, self.y1 - self.ny * self.res)
        return float(w), float(s), float(e), float(n)

    def index_of(self, lon, lat):
        """(row, col) of the pixels containing lon/lat; -1 outside."""
        x, y = lonlat_to_merc(lon, lat)
        col = np.floor((x - self.x0) / self.res).astype(int)
        row = np.floor((self.y1 - y) / self.res).astype(int)
        inside = (col >= 0) & (col < self.nx) & (row >= 0) & (row < self.ny)
        return np.where(inside, row, -1), np.where(inside, col, -1)

    def to_dict(self):
        w, s, e, n = self.bounds_lonlat()
        return {"crs": "EPSG:3857", "x0": self.x0, "y1": self.y1, "res": self.res, "nx": self.nx, "ny": self.ny,
                "bounds": [w, s, e, n]}


def weather_axes(region):
    """Longitudes and latitudes of the coarse weather grid (covers the region with one step of margin)."""
    step = region.weather_step
    lons = np.round(np.arange(region.west, region.east + step + 1e-9, step), 4)
    lats = np.round(np.arange(region.south, region.north + step + 1e-9, step), 4)
    return lons, lats


def interp_weights(axis, values):
    """Indices and weights for linear interpolation of `values` on a regular increasing `axis`."""
    pos = np.clip((np.asarray(values) - axis[0]) / (axis[1] - axis[0]), 0, len(axis) - 1 - 1e-9)
    i0 = np.floor(pos).astype(int)
    return i0, pos - i0


def bilinear(field, lon_w, lat_w):
    """Interpolate field[lat, lon] (coarse) on a separable lon (columns) x lat (rows) target grid."""
    (ix, fx), (iy, fy) = lon_w, lat_w
    top = field[iy][:, ix] * (1 - fx) + field[iy][:, ix + 1] * fx
    bottom = field[iy + 1][:, ix] * (1 - fx) + field[iy + 1][:, ix + 1] * fx
    return top * (1 - fy)[:, None] + bottom * fy[:, None]
