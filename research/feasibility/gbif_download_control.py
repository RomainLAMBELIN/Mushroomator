"""Download the effort-control taxon (Fagus sylvatica, iNaturalist research grade, France).

Usage: python gbif_download_control.py OUT_CSV
"""
import csv, json, sys, time, urllib.parse, urllib.request

API = "https://api.gbif.org/v1"
FIELDS = ["key", "datasetKey", "species", "genus", "decimalLatitude", "decimalLongitude",
          "coordinateUncertaintyInMeters", "eventDate", "year", "month", "day", "recordedBy"]
INAT = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"


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


def main(out_csv):
    base = {"taxonKey": 2882316, "country": "FR", "hasCoordinate": "true", "hasGeospatialIssue": "false",
            "occurrenceStatus": "PRESENT", "basisOfRecord": "HUMAN_OBSERVATION", "year": "2011,2024",
            "month": "6,12", "datasetKey": INAT, "limit": 300}
    rows, offset = [], 0
    while True:
        d = get(f"{API}/occurrence/search?" + urllib.parse.urlencode(dict(base, offset=offset)))
        rows += [{f: r.get(f) for f in FIELDS} for r in d["results"]]
        offset += len(d["results"])
        if d["endOfRecords"] or not d["results"]:
            break
        time.sleep(0.3)
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
