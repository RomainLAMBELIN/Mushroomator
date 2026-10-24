"""Feasibility: count GBIF occurrences in France for key edible species."""
import json, sys, time, urllib.parse, urllib.request

SPECIES = [
    ("Boletus edulis", "Cèpe de Bordeaux"),
    ("Boletus pinophilus", "Cèpe des pins"),
    ("Boletus aereus", "Cèpe bronzé / tête de nègre"),
    ("Boletus reticulatus", "Cèpe d'été / réticulé"),
    ("Imleria badia", "Bolet bai"),
    ("Cantharellus cibarius", "Girolle"),
    ("Craterellus cornucopioides", "Trompette de la mort"),
    ("Craterellus tubaeformis", "Chanterelle en tube"),
    ("Craterellus lutescens", "Chanterelle jaune"),
    ("Hydnum repandum", "Pied de mouton"),
    ("Hydnum rufescens", "Pied de mouton roux"),
    ("Morchella esculenta", "Morille commune"),
    ("Morchella", "Morilles (genre)"),
    ("Lactarius deliciosus", "Lactaire délicieux"),
    ("Macrolepiota procera", "Coulemelle"),
    ("Calocybe gambosa", "Mousseron de la Saint-Georges"),
    ("Marasmius oreades", "Faux mousseron"),
    ("Lepista nuda", "Pied bleu"),
    ("Pleurotus ostreatus", "Pleurote en huître"),
    ("Amanita caesarea", "Oronge"),
    ("Russula cyanoxantha", "Russule charbonnière"),
    ("Agaricus campestris", "Rosé des prés"),
    ("Sparassis crispa", "Sparassis crépu"),
    ("Tricholoma portentosum", "Petit-gris / tricholome prétentieux"),
    ("Hygrophorus marzuolus", "Hygrophore de mars"),
    ("Infundibulicybe geotropa", "Tête de moine"),
    ("Laetiporus sulphureus", "Polypore soufré"),
    ("Fistulina hepatica", "Langue de boeuf"),
]

API = "https://api.gbif.org/v1"

def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            time.sleep(2 ** attempt)
            last = e
    raise last

def main():
    rows = []
    for sci, fr in SPECIES:
        m = get(f"{API}/species/match?" + urllib.parse.urlencode({"name": sci, "kingdom": "Fungi"}))
        key = m.get("usageKey")
        if key is None:
            rows.append({"sci": sci, "fr": fr, "key": None})
            continue
        base = {"taxonKey": key, "country": "FR", "hasCoordinate": "true", "hasGeospatialIssue": "false", "limit": 0}
        q = dict(base, facet=["month", "basisOfRecord"], facetLimit=20)
        url = f"{API}/occurrence/search?" + urllib.parse.urlencode(q, doseq=True)
        d = get(url)
        months = {int(c["name"]): c["count"] for f in d.get("facets", []) if f["field"] == "MONTH" for c in f["counts"]}
        bor = {c["name"]: c["count"] for f in d.get("facets", []) if f["field"] == "BASIS_OF_RECORD" for c in f["counts"]}
        # records since 2015 with uncertainty <= 1 km would be the most useful for daily weather modelling
        q2 = dict(base, year="2015,2026", coordinateUncertaintyInMeters="0,1000")
        d2 = get(f"{API}/occurrence/search?" + urllib.parse.urlencode(q2))
        q3 = dict(base, year="2015,2026")
        d3 = get(f"{API}/occurrence/search?" + urllib.parse.urlencode(q3))
        # Europe-wide (useful for transfer learning)
        q4 = {"taxonKey": key, "continent": "EUROPE", "hasCoordinate": "true", "limit": 0}
        d4 = get(f"{API}/occurrence/search?" + urllib.parse.urlencode(q4))
        rows.append({
            "sci": sci, "fr": fr, "key": key, "matched": m.get("scientificName"),
            "count_fr": d["count"], "count_fr_2015p": d3["count"], "count_fr_2015p_unc1km": d2["count"],
            "count_europe": d4["count"], "months": months, "basis": bor,
        })
        print(sci, d["count"], d3["count"], d2["count"], d4["count"], file=sys.stderr)
        time.sleep(0.2)
    json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
