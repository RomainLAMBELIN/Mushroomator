"""Project-wide settings: region, grids, paths."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("MUSHROOMATOR_DATA", ROOT / "data"))   # downloads and caches (not versioned)
ASSETS_DIR = ROOT / "assets"                                           # built layers and models (versioned)
WEB_DIR = ROOT / "web"                                                 # static application sources
SITE_DIR = Path(os.environ.get("MUSHROOMATOR_SITE", ROOT / "site"))  # generated site (not versioned)


@dataclass(frozen=True)
class Region:
    key: str
    name: str
    west: float
    south: float
    east: float
    north: float
    departments: tuple       # BD Forêt departments covering the region (French part)
    pixel_m: float = 250.0   # Web Mercator pixel size (≈ 175 m on the ground at 45°N)
    weather_step: float = 0.2  # spacing of the weather grid, in degrees

    @property
    def bbox(self):
        return (self.west, self.south, self.east, self.north)


RHONE_ALPES = Region(
    key="rhone-alpes",
    name="Rhône-Alpes et alentours",
    west=3.3, south=43.9, east=7.3, north=46.8,
    departments=("01", "03", "04", "05", "07", "12", "15", "25", "26", "30", "38", "39", "42", "43",
                 "48", "63", "69", "71", "73", "74", "84"),
)

REGIONS = {RHONE_ALPES.key: RHONE_ALPES}
DEFAULT_REGION = RHONE_ALPES.key

# Training domain for the weather-trigger models (must lie inside the E-OBS extract).
TRAIN_COUNTRIES = ("FR", "CH")
TRAIN_YEARS = (2011, 2024)
LAPSE_RATE = -0.0065   # °C per metre, used to move temperatures between elevations
