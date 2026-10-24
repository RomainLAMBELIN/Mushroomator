"""Host groups: BD Forêt V2 vegetation-formation classes (CODE_TFV) grouped by fungal host value."""

# Order defines the raster codes (1-based); 0 means "no BD Forêt formation" (fields, towns, water, abroad).
HOST_GROUPS = (
    ("chene_decidu", "Chênes décidus"),
    ("chene_sempervirent", "Chênes verts ou lièges"),
    ("hetre", "Hêtre"),
    ("chataignier", "Châtaignier"),
    ("robinier", "Robinier"),
    ("peupleraie", "Peupleraie"),
    ("feuillu_autre", "Autre feuillu pur"),
    ("feuillus_melange", "Feuillus mélangés"),
    ("pin_sylvestre", "Pin sylvestre"),
    ("pin_noir", "Pin noir ou laricio"),
    ("pin_autre", "Autres pins"),
    ("pin_montagne", "Pin à crochets ou cembro"),
    ("sapin_epicea", "Sapin ou épicéa"),
    ("meleze", "Mélèze"),
    ("douglas", "Douglas"),
    ("conifere_autre", "Autres conifères"),
    ("mixte_feuillus", "Mixte à feuillus dominants"),
    ("mixte_coniferes", "Mixte à conifères dominants"),
    ("sans_couvert", "Forêt sans couvert arboré"),
    ("lande", "Lande"),
    ("herbacee", "Formation herbacée"),
)
GROUP_CODE = {key: i + 1 for i, (key, _) in enumerate(HOST_GROUPS)}

_TFV_TO_GROUP = {
    "FF0": "sans_couvert",
    "FO0": "sans_couvert",
    "FF1-00": "feuillus_melange",       # feuillus purs en îlots
    "FF1-00-00": "feuillus_melange",
    "FF1-09-09": "hetre",
    "FF1-10-10": "chataignier",
    "FF1-14-14": "robinier",
    "FF1-49-49": "feuillu_autre",
    "FF1G01-01": "chene_decidu",
    "FF1G06-06": "chene_sempervirent",
    "FF2-00": "conifere_autre",         # conifères purs en îlots
    "FF2-00-00": "conifere_autre",
    "FF2-51-51": "pin_autre",           # pin maritime
    "FF2-52-52": "pin_sylvestre",
    "FF2-57-57": "pin_autre",           # pin d'Alep
    "FF2-63-63": "meleze",
    "FF2-64-64": "douglas",
    "FF2-80-80": "pin_autre",
    "FF2-81-81": "pin_autre",
    "FF2-90-90": "conifere_autre",
    "FF2-91-91": "conifere_autre",
    "FF2G53-53": "pin_noir",
    "FF2G58-58": "pin_montagne",
    "FF2G61-61": "sapin_epicea",
    "FF31": "mixte_feuillus",
    "FF32": "mixte_coniferes",
    "FO1": "feuillus_melange",
    "FO2": "conifere_autre",
    "FO3": "mixte_coniferes",
    "FP": "peupleraie",
    "LA4": "lande",
    "LA6": "herbacee",
}
_PREFIX_FALLBACK = (("FF1", "feuillus_melange"), ("FF2", "conifere_autre"), ("FF3", "mixte_coniferes"),
                    ("FO", "mixte_coniferes"), ("LA", "lande"))


def group_of_tfv(code_tfv):
    """Host-group code (1..21) for a BD Forêt CODE_TFV, 0 if unknown."""
    code = (code_tfv or "").strip()
    if code in _TFV_TO_GROUP:
        return GROUP_CODE[_TFV_TO_GROUP[code]]
    for prefix, group in _PREFIX_FALLBACK:
        if code.startswith(prefix):
            return GROUP_CODE[group]
    return 0
