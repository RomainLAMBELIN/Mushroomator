# Étude de faisabilité : reproduire les résultats

Scripts de l'étude décrite dans [`docs/recherche/05-etude-de-faisabilite.md`](../../docs/recherche/05-etude-de-faisabilite.md). Ils téléchargent des données publiques (GBIF, E-OBS) et recalculent les tableaux et les figures.

Les données téléchargées sont volumineuses et ne sont pas versionnées : placez-les dans un dossier hors du dépôt (ici `$DATA`).

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Étapes

```bash
DATA=/chemin/vers/donnees
mkdir -p $DATA/eobs $DATA/gbif

# 1. Inventaire GBIF par espèce (France / Europe, saisonnalité brute) -> results/gbif_counts_france.json
.venv/bin/python gbif_counts.py > results/gbif_counts_france.json
# 2. Saisonnalité nettoyée (hors dates au 1er du mois) -> results/gbif_seasonality_france.json
.venv/bin/python gbif_seasonality.py results/gbif_counts_france.json > results/gbif_seasonality_france.json

# 3. Observations des 6 espèces étudiées + témoin d'effort (hêtre, iNaturalist)
.venv/bin/python gbif_download.py $DATA/gbif
.venv/bin/python gbif_download_control.py $DATA/gbif/Fagus_sylvatica.csv

# 4. Météo E-OBS v30.0e (pluie et température moyenne, 2011 -> 06/2024, ~1,1 Go) puis extraction France
for v in rr tg; do
  curl -o $DATA/eobs/${v}_ens_mean_0.1deg_reg_2011-2024_v30.0e.nc \
    "https://knmi-ecad-assets-prd.s3.amazonaws.com/ensembles/data/Grid_0.1deg_reg_ensemble/${v}_ens_mean_0.1deg_reg_2011-2024_v30.0e.nc"
done
.venv/bin/python eobs_subset.py $DATA/eobs $DATA/eobs_france.npz

# 5. Modèles et validation (~10 min sur 4 cœurs) -> $DATA/results/summary.csv
.venv/bin/python feasibility.py $DATA/eobs_france.npz $DATA/gbif $DATA/results
# 6. Importance des groupes de variables
.venv/bin/python feasibility_importance.py $DATA/results
# 7. Figures (versions claire et sombre)
.venv/bin/python feasibility_figures.py $DATA/eobs_france.npz $DATA/results ../../docs/recherche/figures
```

Les résultats agrégés de la version publiée sont dans [`results/`](results/) (`summary.csv`, inventaire et saisonnalité GBIF). Les observations GBIF évoluant chaque semaine, un nouveau téléchargement peut donner des chiffres légèrement différents.

## Licences des données

- **E-OBS** : usage réservé à la recherche et à l'enseignement non commerciaux (citer Cornes et al. 2018 et le projet ECA&D). Ne pas l'utiliser dans un produit commercial.
- **GBIF** : chaque jeu de données a sa licence (CC0, CC-BY, CC-BY-NC) ; citer le DOI du téléchargement en cas de publication.

## Fichiers

| Fichier | Rôle |
|---|---|
| `gbif_counts.py` | nombre d'observations par espèce (France, depuis 2015, incertitude ≤ 1 km, Europe) et saisonnalité brute |
| `gbif_seasonality.py` | saisonnalité mensuelle hors dates par défaut |
| `gbif_download.py`, `gbif_download_control.py` | téléchargement des observations utilisées pour les modèles |
| `eobs_subset.py` | extraction de la France dans les grilles E-OBS |
| `feasibility.py` | jeux de données (observations + 10 dates témoins au même lieu), variables météo décalées, modèles et validation croisée |
| `feasibility_importance.py` | importance par permutation de groupes de variables |
| `feasibility_figures.py` | figures du chapitre 5 |
