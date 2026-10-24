"""The map is computed by web/model.js; it must match mushroomator/predict.py."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from mushroomator import layers, predict, site
from mushroomator.config import RHONE_ALPES, ROOT
from mushroomator.grid import weather_axes

STEP = 37
pytestmark = pytest.mark.skipif(shutil.which("node") is None or not (ROOT / "assets/regions/rhone-alpes/layers.json").exists(),
                                reason="node or regional layers unavailable")


def synthetic_weather():
    lons, lats = weather_axes(RHONE_ALPES)
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    days = 3
    smooth = lambda a, b, c: (a + b * np.sin(la * 1.3 + c) + b * np.cos(lo * 0.9 - c))  # noqa: E731
    feats = {"T14_sl": [smooth(16, 3, d).round(2).tolist() for d in range(days)],
             "P30": [np.clip(smooth(70, 40, d), 0, None).round(1).tolist() for d in range(days)],
             "P_7_21": [np.clip(smooth(25, 15, d), 0, None).round(1).tolist() for d in range(days)],
             "SWB": [np.clip(smooth(0.6, 0.3, d), 0, 1).round(3).tolist() for d in range(days)]}
    return {"lons": lons.tolist(), "lats": lats.tolist(), "dates": ["2023-10-11", "2023-10-12", "2023-10-13"],
            "features": feats}


def test_js_map_matches_python(tmp_path):
    payload = site.species_payload(RHONE_ALPES.key)
    if not payload:
        pytest.skip("no trained models")
    weather = synthetic_weather()
    L = layers.load(RHONE_ALPES.key)
    (tmp_path / "w.json").write_text(json.dumps(weather))
    (tmp_path / "sp.json").write_text(json.dumps(payload))
    script = tmp_path / "run.mjs"
    script.write_text(f"""
import * as M from {json.dumps((ROOT / 'web/model.js').as_uri())};
import {{ readFileSync }} from "node:fs";
import {{ gunzipSync }} from "node:zlib";
const dir = {json.dumps(str(ROOT / 'assets/regions/rhone-alpes'))};
const meta = JSON.parse(readFileSync(dir + "/layers.json"));
const load = (f, T) => {{ const b = gunzipSync(readFileSync(dir + "/" + f)); return new T(b.buffer, b.byteOffset, b.byteLength / T.BYTES_PER_ELEMENT); }};
const layers = {{ grid: meta.grid, host: load("host.u8.gz", Uint8Array), elev: load("elev.u16.gz", Uint16Array), ph10: load("ph10.u8.gz", Uint8Array) }};
const weather = JSON.parse(readFileSync({json.dumps(str(tmp_path / 'w.json'))}));
const species = JSON.parse(readFileSync({json.dumps(str(tmp_path / 'sp.json'))}));
const axes = M.gridAxes(meta.grid);
const wts = {{ lon: M.axisWeights(weather.lons, axes.lon), lat: M.axisWeights(weather.lats, axes.lat) }};
const out = {{}};
for (const sp of species) {{
  const fields = M.coarseFields(sp, weather, 1);
  out[sp.key] = Array.from(M.computeGrid(sp, layers, fields, wts, "indice", 0.15, {STEP}), (v) => (v === v ? v : null));
}}
console.log(JSON.stringify(out));
""")
    res = subprocess.run(["node", str(script)], capture_output=True, text=True, check=True)
    js = json.loads(res.stdout)
    for sp in payload:
        py = predict.index(sp, L, weather, 1)[::STEP, ::STEP].ravel()
        got = np.array([np.nan if v is None else v for v in js[sp["key"]]])
        assert np.array_equal(np.isnan(py), np.isnan(got)), sp["key"]
        ok = ~np.isnan(py)
        assert ok.sum() > 100
        assert np.abs(py[ok] - got[ok]).max() < 2e-3, sp["key"]


def test_web_files_exist():
    for f in ("index.html", "app.js", "model.js", "style.css", "sw.js", "manifest.webmanifest", "icons/icon-192.png",
              "vendor/leaflet/leaflet.js"):
        assert (Path(ROOT) / "web" / f).exists(), f


def test_offline_files_and_version(tmp_path, monkeypatch):
    """sw.js lists the files to keep offline; its version follows the application and data, not the daily weather."""
    monkeypatch.setattr(site, "SITE_DIR", tmp_path / "site")
    sw = tmp_path / "site" / "sw.js"
    version = lambda: re.search(r'const VERSION = "([^"]+)";', sw.read_text()).group(1)  # noqa: E731
    site.build(RHONE_ALPES.key, {"today": "2023-10-12"}, log=lambda *a: None)
    first = version()
    files = json.loads(re.search(r"const FILES = (\[.*\]);", sw.read_text()).group(1))
    assert {"./", "app.js", "data/rhone-alpes/weather.json", "data/rhone-alpes/host.u8.gz"} <= set(files)
    assert "data/rhone-alpes/forest.u8.gz" not in files          # not read by the web application
    assert all((tmp_path / "site" / f).is_file() for f in files if f != "./")
    meta = json.loads((tmp_path / "site/data/rhone-alpes/layers.json").read_text())
    assert set(meta["files"]) == set(site.WEB_LAYERS) and "38" in meta["departements"]
    site.build(RHONE_ALPES.key, {"today": "2023-10-13"}, log=lambda *a: None)
    assert version() == first != "mushroomator-dev"
    web = tmp_path / "web"
    shutil.copytree(ROOT / "web", web)
    (web / "app.js").write_text((web / "app.js").read_text() + "\n// nouvelle version\n")
    monkeypatch.setattr(site, "WEB_DIR", web)
    site.build(RHONE_ALPES.key, log=lambda *a: None)
    assert version() != first
