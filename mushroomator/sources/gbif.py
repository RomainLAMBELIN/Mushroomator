"""GBIF occurrences with the quality filters established in the research phase (docs/recherche/02).

Data: GBIF.org occurrence records; each dataset keeps its own licence (CC0, CC-BY or CC-BY-NC).
"""
import time
from pathlib import Path

import pandas as pd

from .. import net
from ..config import DATA_DIR

API = "https://api.gbif.org/v1"
FIELDS = ["key", "datasetKey", "scientificName", "decimalLatitude", "decimalLongitude",
          "coordinateUncertaintyInMeters", "eventDate", "year", "month", "day", "countryCode", "license"]
# Synthetic département-level atlas, every record dated 2016-04-01 (see docs/recherche/02-sources-de-donnees.md).
EXCLUDED_DATASETS = {"23bab45d-e5c8-43fd-8fc5-6a8668becd16"}
MAX_UNCERTAINTY_M = 5000

# Common forest macrofungi used as "target group": they share the observers' effort of the target species.
TARGET_GROUP = [
    "Amanita muscaria", "Amanita rubescens", "Amanita citrina", "Amanita phalloides", "Amanita excelsa",
    "Russula ochroleuca", "Russula nigricans", "Russula fellea", "Lactarius blennius", "Lactarius quietus",
    "Laccaria amethystina", "Laccaria laccata", "Xerocomellus chrysenteron", "Imleria badia", "Suillus luteus",
    "Tricholoma saponaceum", "Hypholoma fasciculare", "Armillaria mellea", "Fomes fomentarius",
    "Fomitopsis pinicola", "Trametes versicolor", "Mycena galericulata", "Clitocybe nebularis",
    "Paxillus involutus", "Scleroderma citrinum", "Lycoperdon perlatum", "Gymnopus dryophilus",
    "Hygrophoropsis aurantiaca", "Neoboletus luridiformis", "Calocera viscosa",
]


def taxon_key(name, kingdom="Fungi"):
    m = net.get_json(f"{API}/species/match", params={"name": name, "kingdom": kingdom})
    if "usageKey" not in m:
        raise LookupError(f"Taxon inconnu dans GBIF : {name}")
    return m["usageKey"]


def search(params, page=300, pause=0.2):
    """All records matching `params` (GBIF search API, at most 100 000)."""
    rows, offset = [], 0
    while True:
        d = net.get_json(f"{API}/occurrence/search", params={**params, "limit": page, "offset": offset})
        rows += [{f: r.get(f) for f in FIELDS} for r in d["results"]]
        offset += len(d["results"])
        if d["endOfRecords"] or not d["results"] or offset >= 100_000:
            return rows
        time.sleep(pause)


def occurrences(name, countries=("FR",), years=(2011, 2024), bbox=None, cache=True):
    """Raw human observations of a taxon (cached as CSV under data/gbif)."""
    tag = "-".join(countries) + f"_{years[0]}-{years[1]}" + ("" if bbox is None else "_bbox" + "_".join(f"{v:g}" for v in bbox))
    path = Path(DATA_DIR / "gbif" / f"{name.replace(' ', '_')}_{tag}.csv")
    if cache and path.exists():
        return pd.read_csv(path, low_memory=False)
    key = taxon_key(name)
    rows = []
    for country in countries:
        params = {"taxonKey": key, "country": country, "hasCoordinate": "true", "hasGeospatialIssue": "false",
                  "occurrenceStatus": "PRESENT", "basisOfRecord": "HUMAN_OBSERVATION", "year": f"{years[0]},{years[1]}"}
        if bbox is not None:
            w, s, e, n = bbox
            params |= {"decimalLatitude": f"{s},{n}", "decimalLongitude": f"{w},{e}"}
        rows += search(params)
    df = pd.DataFrame(rows, columns=FIELDS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def clean(df):
    """Apply the quality filters; adds a `date` column. Drops default dates, ranges and imprecise points."""
    df = df[~df["datasetKey"].isin(EXCLUDED_DATASETS)]
    df = df[df["day"].notna() & df["month"].notna() & (df["day"] != 1)]
    ev = df["eventDate"].astype(str)
    df = df[(ev.str.len() >= 10) & ~ev.str.contains("/")]
    unc = pd.to_numeric(df["coordinateUncertaintyInMeters"], errors="coerce")
    df = df[unc.isna() | (unc <= MAX_UNCERTAINTY_M)].copy()
    df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=df.day), errors="coerce")
    df = df[df["date"].notna()]
    return df.drop_duplicates(["decimalLatitude", "decimalLongitude", "date"]).reset_index(drop=True)

