# Essais « identifier les coins » (25/10/2026)

Les variables fines disponibles en open data situent-elles les coins à champignons ? Résultats et lecture : [chapitre 8, section 8.7](../../docs/recherche/08-identifier-les-coins.md#87-résultats-des-essais-du-25102026). Les chiffres bruts sont dans `resultats/`.

Environnement : `pip install -r requirements-build.txt`. Les données téléchargées (observations, extraits LiDAR, chemins, BD Forêt) vont dans un dossier de travail à part, jamais dans le dépôt ; tous les scripts prennent leurs chemins en arguments.

| Étape | Commande |
|---|---|
| Observations GBIF France ≤ 50 m (9 espèces + 30 champignons forestiers courants) | `fetch_obs.py <dépôt> obs_raw.json` |
| Dédoublonnage, 5 000 points de comparaison | `prepare_points.py points obs_raw.json points_sel.json` |
| Hauteur de végétation LiDAR HD (120 m au pas de 1 m) et relief RGE ALTI (400 m au pas de 5 m) autour de chaque point, Géoplateforme | `extract_wms.py points_sel.json wms/ [fils]` |
| Variables fines (végétation dans des rayons de 10, 25, 50 m ; pente, exposition, creux et bosses, courbure, humidité) | `features.py points_sel.json wms/ features.json` |
| Habitat de l'application (région) et BD Forêt au point | `hab_region.py <dépôt> points_sel.json hab_region.json` ; `bdforet_points.py <dépôt> points.json bdforet.json` |
| **Test 1** : face aux autres champignons | `test1_autres_champignons.py points_sel.json features.json hab_region.json resultats.json` |
| Cas des tests appariés | `prepare_points.py cas points_sel.json features.json cases.json` |
| Témoins à 60–400 m, même distance d'un chemin (BD TOPO) | `temoins_proches.py cases.json strates.json chemins/` puis `extract_wms.py` et `features.py` sur les témoins |
| Distance aux cours d'eau ; BD Forêt au point | `hydro.py strates.json hydro.json eau/` ; `bdforet_points.py` |
| **Test 2** : coin face à son voisinage | `test2_coin_voisinage.py strates.json features.json,features_temoins.json resultats.json hydro.json bdforet.json` |
| Témoins à 0,5–5 km, même distance d'un chemin | `temoins_parcelles.py strates_test2.json strates.json chemins5km/` puis `extract_wms.py` et `features.py` |
| BD Forêt des autres départements | `download_bdforet.py <dépôt> departements.json` puis `bdforet_points.py` |
| **Test 3** : parcelle face aux forêts alentour | `test3_parcelles.py strates.json features.json,features_temoins.json resultats.json - bdforet.json` |
| **Test 4** : persistance des coins (observations ≤ 100 m avec auteur et date) | `fetch_obs_auteurs.py <dépôt> obs.json` puis `test4_persistance.py obs.json resultats.json` |
