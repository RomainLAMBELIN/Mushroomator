"""Download GBIF occurrences (France) for the feasibility study.

Usage: python gbif_download.py OUT_DIR
"""
import csv, json, sys, time, urllib.parse, urllib.request

API = "https://api.gbif.org/v1"
SPECIES = ["Boletus edulis", "Cantharellus cibarius", "Macrolepiota procera",
           "Craterellus cornucopioides", "Hydnum repandum", "Morchella"]
# Synthetic département-level atlas with default dates (2016-04-01): not real observations.
EXCLUDED_DATASETS = {"23bab45d-e5c8-43fd-8fc5-6a8668becd16"}
FIELDS = ["key", "datasetKey", "species", "genus", "decimalLatitude", "decimalLongitude",
          "coordinateUncertaintyInMeters", "eventDate", "year", "month", "day", "recordedBy"]


def get(url):
    last = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** attempt)
    raise last


def main(out_dir):
    for name in SPECIES:
        m = get(f"{API}/species/match?" + urllib.parse.urlencode({"name": name, "kingdom": "Fungi"}))
        key = m["usageKey"]
        base = {"taxonKey": key, "country": "FR", "hasCoordinate": "true", "hasGeospatialIssue": "false",
                "occurrenceStatus": "PRESENT", "basisOfRecord": "HUMAN_OBSERVATION", "year": "2011,2024",
                "limit": 300}
        rows, offset = [], 0
        while True:
            d = get(f"{API}/occurrence/search?" + urllib.parse.urlencode(dict(base, offset=offset)))
            for r in d["results"]:
                rows.append({f: r.get(f) for f in FIELDS})
            offset += len(d["results"])
            if d["endOfRecords"] or not d["results"]:
                break
            time.sleep(0.3)
        kept = [r for r in rows if r["datasetKey"] not in EXCLUDED_DATASETS]
        fn = f"{out_dir}/{name.replace(' ', '_')}.csv"
        with open(fn, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(kept)
        print(f"{name}: {len(rows)} downloaded, {len(kept)} kept -> {fn}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
