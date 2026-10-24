"""Habitat suitability H(x) = host × elevation × soil pH (same formulas as web/app.js)."""
import tomllib
from pathlib import Path

import numpy as np

from .hosts import HOST_GROUPS

SPECIES_FILE = Path(__file__).with_name("species.toml")
ELEV_FLOOR = 0.05   # residual suitability outside the elevation range


def load_species():
    return tomllib.loads(SPECIES_FILE.read_text(encoding="utf-8"))


def host_table(spec):
    """Suitability of host-group codes 0..N (0 = no forest formation)."""
    return np.array([0.0] + [float(spec["hotes"].get(key, 0.0)) for key, _ in HOST_GROUPS], dtype=np.float32)


def ph_factor(ph, spec):
    a, b = spec["ph"]          # suitability = ph_bas at pH a, 1 at pH b, linear in between
    low = spec.get("ph_bas", 0.5)
    frac = np.clip((np.asarray(ph, dtype=float) - a) / (b - a), 0.0, 1.0)
    out = low + (1.0 - low) * frac
    return np.where(np.isfinite(ph), out, 1.0)   # unknown soil: no penalty


def elevation_factor(z, spec):
    z0, z1, z2, z3 = spec["altitude"]
    z = np.asarray(z, dtype=float)
    up = np.clip((z - z0) / max(z1 - z0, 1.0), 0.0, 1.0)
    down = np.clip((z3 - z) / max(z3 - z2, 1.0), 0.0, 1.0)
    out = ELEV_FLOOR + (1.0 - ELEV_FLOOR) * np.minimum(up, down)
    return np.where(np.isfinite(z), out, 0.0)


def suitability(layers, spec):
    """H in [0, 1] for every pixel of the region."""
    host = host_table(spec)[layers.host]
    return (host * elevation_factor(layers.elev, spec) * ph_factor(layers.ph, spec)).astype(np.float32)
