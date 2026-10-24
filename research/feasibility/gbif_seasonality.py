"""Monthly share of GBIF records in France per species, excluding records dated on the 1st of a month
(default dates, including the synthetic 2016-04-01 departmental atlas records).

Usage: python gbif_seasonality.py GBIF_COUNTS_JSON > seasonality.json
"""
import json, sys, time, urllib.parse, urllib.request

API = "https://api.gbif.org/v1"


def month_counts(params):
    q = dict(params, limit=0, facet="month", facetLimit=12)
    with urllib.request.urlopen(f"{API}/occurrence/search?" + urllib.parse.urlencode(q), timeout=60) as r:
        d = json.load(r)
    return {int(c["name"]): c["count"] for f in d["facets"] for c in f["counts"]}


def main(counts_json):
    out = []
    for r in json.load(open(counts_json)):
        base = {"taxonKey": r["key"], "country": "FR", "hasCoordinate": "true", "hasGeospatialIssue": "false"}
        allm, day1 = month_counts(base), month_counts(dict(base, day=1))
        clean = {m: allm.get(m, 0) - day1.get(m, 0) for m in range(1, 13)}
        tot = sum(clean.values())
        out.append({"sci": r["sci"], "fr": r["fr"], "n_clean": tot,
                    "share": {m: round(100 * v / tot, 1) if tot else 0 for m, v in clean.items()}})
        time.sleep(0.2)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
