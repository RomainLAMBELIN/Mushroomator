import datetime as dt

import numpy as np

from mushroomator import weather
from mushroomator.config import LAPSE_RATE, Region


def fake_open_meteo(n_days):
    """Mimic the Open-Meteo multi-location answer: one dict per requested point."""
    def get_json(url, params=None, **kwargs):
        lats = [float(v) for v in params["latitude"].split(",")]
        start = dt.date(2026, 10, 24) - dt.timedelta(days=weather.PAST_DAYS)
        dates = [(start + dt.timedelta(days=k)).isoformat() for k in range(n_days)]
        out = []
        for la in lats:
            out.append({"latitude": la, "elevation": 500.0 + 100 * (la - 45),
                        "daily": {"time": dates, "precipitation_sum": [2.0] * n_days,
                                  "temperature_2m_mean": [10.0 + (la - 45)] * n_days,
                                  "temperature_2m_max": [15.0] * n_days}})
        out[0]["daily"]["temperature_2m_mean"][5] = None      # a missing value is interpolated
        return out
    return get_json


def test_fetch_and_export(monkeypatch, tmp_path):
    region = Region("test", "Test", 5.0, 45.0, 5.4, 45.4, (), weather_step=0.2)
    monkeypatch.setattr(weather, "DATA_DIR", tmp_path)
    monkeypatch.setattr(weather, "ASSETS_DIR", tmp_path)
    monkeypatch.setattr(weather.net, "get_json", fake_open_meteo(weather.PAST_DAYS + weather.FORECAST_DAYS))
    monkeypatch.setattr(weather.time, "sleep", lambda s: None)
    raw = weather.fetch(region, dt.date(2026, 10, 24), log=lambda *a: None)
    assert len(raw["rr"]) == 16          # 4 x 4 points: the grid has one step of margin beyond the region
    assert len(raw["dates"]) == weather.PAST_DAYS + weather.FORECAST_DAYS
    out = weather.export(region, raw)
    assert out["today"] == "2026-10-24"
    assert len(out["dates"]) == weather.SHOW_PAST + weather.SHOW_FUTURE + 1
    p30 = np.array(out["features"]["P30"])
    assert p30.shape == (15, 4, 4) and np.allclose(p30, 60.0)
    # temperatures are exported at sea level: T_sl = T - lapse * z
    t_sl = np.array(out["features"]["T14_sl"])
    elev = np.array(out["elev"])
    t_point = t_sl - (-LAPSE_RATE) * elev[None]
    assert np.allclose(t_point[:, 1, :], 10.2, atol=0.01)
    assert out["series"]["rr"][0][0] == 2.0
