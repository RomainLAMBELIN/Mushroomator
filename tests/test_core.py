import numpy as np
import pandas as pd
import pytest

from mushroomator import features as feat
from mushroomator import habitat, trigger
from mushroomator.config import RHONE_ALPES
from mushroomator.grid import Grid, bilinear, interp_weights, lonlat_to_merc, merc_to_lonlat, weather_axes
from mushroomator.hosts import GROUP_CODE, HOST_GROUPS, group_of_tfv


def test_rain_and_temperature_windows():
    n, pts = 100, 2
    rr = np.ones((n, pts))
    tg = np.tile(np.arange(n, dtype=float)[:, None], (1, pts))
    f = feat.compute(rr, tg, np.arange(1, n + 1), np.array([45.0, 46.0]))
    t = 80
    assert f["P30"][t, 0] == pytest.approx(30)
    assert f["P_7_21"][t, 0] == pytest.approx(14)
    assert f["P3"][t, 1] == pytest.approx(3)
    assert f["T14"][t, 0] == pytest.approx(np.mean(np.arange(t - 13, t + 1)))
    assert f["dT7"][t, 0] == pytest.approx(7)
    assert np.isnan(f["P30"][feat.HISTORY_DAYS - 2, 0]) and np.isfinite(f["P30"][feat.HISTORY_DAYS - 1, 0])


def test_bucket_bounds_and_drying():
    rr = np.zeros((60, 1))
    pet = np.full((60, 1), 3.0)
    s = feat.bucket(rr, pet)
    assert s[0, 0] < 1 and np.all(np.diff(s[:, 0]) < 0) and s.min() > 0
    wet = feat.bucket(np.full((10, 1), 500.0), pet)
    assert wet.max() == pytest.approx(1.0)


def test_mercator_round_trip_and_pixel_lookup():
    lon, lat = np.array([3.3, 5.7, 7.2]), np.array([44.0, 45.2, 46.7])
    x, y = lonlat_to_merc(lon, lat)
    lon2, lat2 = merc_to_lonlat(x, y)
    assert np.allclose(lon, lon2) and np.allclose(lat, lat2)
    g = Grid.from_region(RHONE_ALPES)
    r, c = g.index_of(g.column_lon()[[10, 500]], g.row_lat()[[20, 700]])
    assert list(r) == [20, 700] and list(c) == [10, 500]


def test_bilinear_reproduces_linear_fields():
    lons, lats = weather_axes(RHONE_ALPES)
    field = 2.0 * lats[:, None] + 3.0 * lons[None, :]
    g = Grid.from_region(RHONE_ALPES)
    lon_c, lat_r = g.column_lon()[::97], g.row_lat()[::89]
    out = bilinear(field, interp_weights(lons, lon_c), interp_weights(lats, lat_r))
    assert np.allclose(out, 2.0 * lat_r[:, None] + 3.0 * lon_c[None, :], atol=1e-9)


def test_host_groups_mapping():
    assert group_of_tfv("FF1-09-09") == GROUP_CODE["hetre"]
    assert group_of_tfv("FF2G61-61") == GROUP_CODE["sapin_epicea"]
    assert group_of_tfv("FF1-99-99") == GROUP_CODE["feuillus_melange"]      # unknown code: prefix fallback
    assert group_of_tfv("") == 0


def test_species_tables_are_complete():
    for key, spec in habitat.load_species().items():
        table = habitat.host_table(spec)
        assert len(table) == len(HOST_GROUPS) + 1 and table[0] == 0, key
        assert set(spec["hotes"]) == {k for k, _ in HOST_GROUPS}, key
        assert ((table >= 0) & (table <= 1)).all(), key
        z0, z1, z2, z3 = spec["altitude"]
        assert z0 <= z1 <= z2 <= z3, key


def test_habitat_factors():
    spec = {"ph": [7.5, 5.5], "ph_bas": 0.4, "altitude": [0, 100, 1500, 1900]}
    assert habitat.ph_factor(np.array([5.0, 6.5, 8.0, np.nan]), spec) == pytest.approx([1.0, 0.7, 0.4, 1.0])
    f = habitat.elevation_factor(np.array([50.0, 800.0, 1700.0, 2500.0]), spec)
    assert f[1] == 1.0 and 0 < f[0] < 1 and 0 < f[2] < 1 and f[3] == pytest.approx(habitat.ELEV_FLOOR)


def test_exported_tables_reproduce_the_model():
    rng = np.random.default_rng(0)
    n = 4000
    X = pd.DataFrame({"doy": rng.integers(1, 366, n).astype(float), "T14": rng.normal(12, 5, n),
                      "P30": rng.gamma(2, 30, n), "P_7_21": rng.gamma(2, 15, n), "SWB": rng.uniform(0, 1, n)})
    logit = -1 + 0.08 * X.T14 - 0.004 * (X.T14 - 13) ** 2 * 10 + 0.01 * X.P30 + np.cos((X.doy - 280) / 58)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    model = trigger.make_model(trigger.FEATURES).fit(X[trigger.FEATURES], y)
    ts = trigger.TrainingSet(X, y, np.zeros(n), np.zeros(n), np.zeros(n), (200, 330))
    intercept, _, tables = trigger.export_tables(model, ts, trigger.FEATURES)
    spec = {"features": trigger.FEATURES, "intercept": intercept, "tables": tables}
    # Linear interpolation between table points: error well below 1 % of the odds.
    assert np.abs(trigger.logit_from_tables(spec, X) - model.decision_function(X[trigger.FEATURES])).max() < 1e-2
