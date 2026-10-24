"""Grouped permutation importance (AUC drop on held-out years) for the season+weather model.

Usage: python feasibility_importance.py RESULTS_DIR
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from feasibility import model

GROUPS = {
    "saison (jour de l'année, lieu)": ["doy_sin", "doy_cos", "lat", "lon"],
    "pluie récente (1-7 j)": ["P1", "P3", "P7"],
    "pluie 2-8 semaines": ["P14", "P21", "P30", "P45", "P60", "P_7_14", "P_14_21", "P_21_28", "P_28_42",
                           "rain_days14", "days_since_10mm"],
    "température": ["T3", "T7", "T14", "T21", "T30", "dT7"],
    "bilan hydrique (seau)": ["SWB", "SWB_mean14"],
}
rng = np.random.default_rng(0)


def main(results):
    for sp in ["Boletus_edulis", "Macrolepiota_procera", "Morchella", "Cantharellus_cibarius"]:
        df = pd.read_csv(Path(results) / f"{sp}_matched_dataset.csv.gz")
        cols = [c for c in df.columns if c not in ("y", "year", "i", "j", "t")]
        drops = {g: [] for g in GROUPS}
        for year in sorted(df.year.unique()):
            te = df.year == year
            if df.y[te].sum() < 15:
                continue
            m = model().fit(df.loc[~te, cols].to_numpy(), df.y[~te].to_numpy())
            Xte, yte = df.loc[te, cols].copy(), df.y[te].to_numpy()
            base = roc_auc_score(yte, m.predict_proba(Xte.to_numpy())[:, 1])
            for g, gcols in GROUPS.items():
                Xp = Xte.copy()
                perm = rng.permutation(len(Xp))
                Xp[gcols] = Xp[gcols].to_numpy()[perm]      # permute the group jointly
                drops[g].append(base - roc_auc_score(yte, m.predict_proba(Xp.to_numpy())[:, 1]))
        print(sp, {g: round(float(np.mean(v)), 3) for g, v in drops.items()})


if __name__ == "__main__":
    main(sys.argv[1])
