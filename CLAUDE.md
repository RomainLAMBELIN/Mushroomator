# Mushroomator : repères pour Claude

## Objectif du projet

Un outil qui aide à **identifier les coins à champignons** : où chercher à l'échelle du coin (10 à 100 m), et quand y aller.
Le *quand* (météo) fonctionne ; le *où* est la priorité : la couche habitat ne fait guère mieux que « c'est une forêt » pour le cèpe et la girolle (AUC ≈ 0,5).
Essais du 25/10/2026 : aucune donnée publique fine (LiDAR HD, relief, eau, BD Forêt au point, observations GBIF) ne situe les coins de cèpe ou de girolle (AUC ≤ 0,6) ; seules les morilles en profitent. Méthode retenue : prospection guidée (peuplement + météo) et carnet de sorties privé dont l'outil apprend (coins semblables, puis calibration).
Résultats, critères et feuille de route : [docs/recherche/08-identifier-les-coins.md](docs/recherche/08-identifier-les-coins.md).

## Repères

- Usage personnel et gratuit (licences non commerciales d'E-OBS et d'Open-Meteo). Interface, documentation et messages de commit en français.
- Paquet Python `mushroomator/` : `python -m mushroomator update | site | serve | layers | train | validate`.
- Application web statique `web/` (Leaflet, indice calculé dans le navigateur, service worker pour le hors-ligne), assemblée dans `site/` par `mushroomator/site.py`.
- Publication sur GitHub Pages par `.github/workflows/carte.yml` : chaque matin, et à chaque push sur la branche par défaut qui touche `web/`, `mushroomator/`, `assets/` ou le workflow.
- Avant de pousser : `python -m pytest -q`, `python -m pyflakes mushroomator tests`, et actionlint si le workflow change.
- Les coins de l'utilisateur sont privés : rien ne doit quitter son téléphone sans son accord.
