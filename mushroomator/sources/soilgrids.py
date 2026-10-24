"""SoilGrids 2.0 → topsoil pH (water) per grid pixel.

Data: ISRIC SoilGrids 2.0 (CC-BY 4.0), Poggio et al. 2021, https://doi.org/10.5194/soil-7-217-2021.
"""
import numpy as np

VRT = "/vsicurl/https://files.isric.org/soilgrids/latest/data/phh2o/phh2o_{depth}_mean.vrt"
DEPTHS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}   # thickness weights for the 0-30 cm average


def build(grid, log=print):
    """Thickness-weighted pH of the 0-30 cm layer (float32, pH units); NaN where unavailable."""
    import rasterio
    from rasterio.warp import Resampling, reproject

    total = np.zeros(grid.shape, dtype=np.float64)
    weight = np.zeros(grid.shape, dtype=np.float64)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="2"):
        for depth, w in DEPTHS.items():
            out = np.full(grid.shape, np.nan, dtype=np.float32)
            with rasterio.open(VRT.format(depth=depth)) as src:
                reproject(rasterio.band(src, 1), out, dst_transform=grid.transform, dst_crs="EPSG:3857",
                          dst_nodata=np.nan, resampling=Resampling.bilinear)
            ok = np.isfinite(out) & (out > 0)
            total[ok] += w * out[ok] / 10.0     # SoilGrids stores pH x 10
            weight[ok] += w
            log(f"  pH SoilGrids {depth} : {ok.mean():.0%} des pixels renseignés")
    with np.errstate(invalid="ignore"):
        return (total / weight).astype(np.float32)
