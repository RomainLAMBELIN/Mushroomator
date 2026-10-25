"""Precise GBIF records in France (declared uncertainty <= 100 m) with observer and date, for the persistence test."""
import json, sys, time, tomllib, urllib.parse, urllib.request
from pathlib import Path

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(ROOT))
from mushroomator.sources.gbif import EXCLUDED_DATASETS, TARGET_GROUP  # noqa: E402

API = "https://api.gbif.org/v1"
def get(path, **params):
    url = f"{API}/{path}?" + urllib.parse.urlencode(params, doseq=True)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mushroomator/0.1 (projet personnel)"}), timeout=90) as r:
                return json.load(r)
        except Exception as e:
            time.sleep(2 ** attempt); last = e
    raise last

species = tomllib.load(open(ROOT / "mushroomator/species.toml", "rb"))
groups = [(k, s["gbif"]) for k, s in species.items()] + [("groupe_cible", TARGET_GROUP)]
rows = []
for group, names in groups:
    for name in names:
        key = get("species/match", name=name, kingdom="Fungi")["usageKey"]
        offset = 0
        while True:
            d = get("occurrence/search", taxonKey=key, country="FR", hasCoordinate="true", hasGeospatialIssue="false",
                    occurrenceStatus="PRESENT", coordinateUncertaintyInMeters="0,100", limit=300, offset=offset)
            for r in d["results"]:
                if r.get("datasetKey") in EXCLUDED_DATASETS:
                    continue
                rows.append({"groupe": group, "nom": name, "lat": r["decimalLatitude"], "lon": r["decimalLongitude"],
                             "incertitude": r.get("coordinateUncertaintyInMeters"), "annee": r.get("year"),
                             "jeu": r.get("datasetKey"), "gbif": r["key"], "auteur": r.get("recordedBy") or r.get("identifiedBy"), "date": r.get("eventDate")})
            offset += len(d["results"])
            if d["endOfRecords"] or not d["results"]:
                break
        print(f"{group:20s} {name:30s} {offset:6d}", flush=True)
OUT.write_text(json.dumps(rows))
print("total", len(rows))
