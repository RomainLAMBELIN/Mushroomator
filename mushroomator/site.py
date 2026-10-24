"""Assemble the static web application: sources from web/, layers and models from assets/, daily weather."""
import hashlib
import json
import shutil

from . import __version__, habitat, trigger
from .config import ASSETS_DIR, REGIONS, SITE_DIR, WEB_DIR
from .features import FEATURE_LABELS, FEATURE_UNITS
from .hosts import HOST_GROUPS
from .layers import region_dir

WEB_LAYERS = ("host", "elev", "ph10")      # layers read by the web application (web/app.js)


def host_values(spec, calibration):
    """Host table (codes 0..N): calibrated on the region's observations when that improved validation."""
    if calibration and calibration.get("hotes_calibres_utilises"):
        return [0.0] + [round(float(calibration["hotes"][key]), 3) for key, _ in HOST_GROUPS]
    return [round(float(v), 3) for v in habitat.host_table(spec)]


def species_payload(region_key):
    validation = ASSETS_DIR / "validation" / f"{region_key}.json"
    report = json.loads(validation.read_text())["species"] if validation.exists() else {}
    out = []
    for key, spec in habitat.load_species().items():
        model_path = trigger.model_dir() / f"{key}.json"
        if not model_path.exists():
            continue
        model = json.loads(model_path.read_text())
        out.append({"key": key, "nom": spec["nom"], "latin": spec["latin"], "confusions": spec["confusions"],
                    "hotes": host_values(spec, report.get(key)),
                    "ph": spec["ph"], "ph_bas": spec.get("ph_bas", 0.5), "altitude": spec["altitude"],
                    "altitude_plancher": habitat.ELEV_FLOOR,
                    "modele": {k: model[k] for k in ("features", "intercept", "tables", "quantiles", "season", "metrics",
                                                      "trained_on")}})
    return out


def build(region_key, weather=None, log=print):
    region = REGIONS[region_key]
    if SITE_DIR.exists():
        for child in SITE_DIR.iterdir():
            if child.name != "data":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(WEB_DIR, SITE_DIR, dirs_exist_ok=True)
    data = SITE_DIR / "data" / region_key
    data.mkdir(parents=True, exist_ok=True)
    for f in data.iterdir():
        if f.name != "weather.json":                 # kept when the site is rebuilt without new weather
            f.unlink()
    meta = json.loads((region_dir(region_key) / "layers.json").read_text())
    meta["files"] = {k: v for k, v in meta["files"].items() if k in WEB_LAYERS}
    meta["departements"] = list(region.departments)        # limits the place search to the mapped departments
    for spec in meta["files"].values():
        shutil.copy2(region_dir(region_key) / spec["file"], data / spec["file"])
    (data / "layers.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    species = species_payload(region_key)
    payload = {"version": __version__, "groupes": ["Aucune formation forestière"] + [label for _, label in HOST_GROUPS],
               "variables": FEATURE_LABELS, "unites": FEATURE_UNITS, "especes": species}
    validation = ASSETS_DIR / "validation" / f"{region_key}.json"
    if validation.exists():
        payload["validation"] = json.loads(validation.read_text())
    (data / "species.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    if weather is not None:
        (data / "weather.json").write_text(json.dumps(weather, separators=(",", ":")))
    (SITE_DIR / "data" / "index.json").write_text(json.dumps(
        {"version": __version__, "regions": [{"key": region.key, "name": region.name}], "default": region.key},
        ensure_ascii=False))
    stamp_service_worker(SITE_DIR)
    log(f"Site prêt dans {SITE_DIR} ({len(species)} espèces)")
    return SITE_DIR


def stamp_service_worker(site_dir):
    """Write into sw.js the files to keep offline and a version that changes with them (the daily weather aside)."""
    files = sorted(p.relative_to(site_dir).as_posix() for p in site_dir.rglob("*")
                   if p.is_file() and p.name not in ("sw.js", "LICENSE"))
    sw = site_dir / "sw.js"
    text = sw.read_text()
    digest = hashlib.sha256(text.encode())
    for name in files:
        if not name.endswith("/weather.json"):
            digest.update(name.encode() + b"\0" + (site_dir / name).read_bytes())
    for old, new in (('const VERSION = "mushroomator-dev";', f'const VERSION = "mushroomator-{digest.hexdigest()[:12]}";'),
                     ('const FILES = ["./"];', f"const FILES = {json.dumps(['./'] + files)};")):
        if old not in text:
            raise RuntimeError(f"sw.js : ligne attendue introuvable : {old}")
        text = text.replace(old, new)
    sw.write_text(text)
