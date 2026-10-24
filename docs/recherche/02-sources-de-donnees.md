# 2. Sources de données

[← Retour au sommaire](README.md)

Inventaire des données utiles, avec leur résolution, leur mode d'accès, leur **licence** (décisive si l'application devient payante) et le résultat d'un test d'accès réalisé depuis l'environnement de recherche le 24/10/2026 (✅ accessible, ❌ inaccessible *depuis cet environnement* : à retester depuis une machine normale).

## 2.1 Observations d'espèces (présences)

| Source | Contenu | Accès | Licence | Test |
|---|---|---|---|---|
| **[GBIF](https://www.gbif.org/)** | Agrégateur mondial. France : **1,25 M** d'observations de champignons (dont lichens), **1,08 M** géolocalisées. Espèces comestibles : 200 à 3 800 observations chacune en France, 1 600 à 92 000 en Europe (détail au [chapitre 1](01-ecologie-fructification.md#14-fiches-espèces-france)) | API REST `api.gbif.org/v1` (recherche ≤ 100 000 lignes), téléchargements en masse avec DOI | par jeu de données : CC-BY 87 %, **CC-BY-NC 11 %**, CC0 2 % (champignons France) | ✅ |
| **iNaturalist** | Observations avec photo ; qualité « recherche » après validation communautaire (757 cèpes de Bordeaux en France) | API `api.inaturalist.org/v1` ; aussi via GBIF | majoritairement CC-BY-NC | ✅ |
| **INPN / [OpenObs](https://openobs.mnhn.fr/)** (PatriNat : OFB, MNHN, CNRS) | Portail national du SINP ; agrège les données des associations mycologiques, de l'ONF, des conservatoires | API documentée sur `openobs.mnhn.fr/api/docs`, export | variable selon le producteur | ❌ (403 depuis l'environnement de recherche) |
| **FongiBase / FongiFrance** (ADONIF, Société mycologique de France) | Base nationale : **1,04 M** d'observations fongiques (2022), 11 556 taxons ; 42,7 % géolocalisées par GPS, 32,9 % au centroïde de commune ; 90,8 % datées au jour ; sud méditerranéen sous-échantillonné ([Gautier et al. 2022](https://doi.org/10.3390/jof8090926)) | en partie transmise au GBIF via le SINP (jeux « FongiFrance », « Inventaire national… ») ; le reste sur demande | à négocier | partiel (via GBIF) |
| Observation.org, Mushroom Observer, atlas nationaux (Danemark ~1 M d'observations, Suisse, Royaume-Uni, Suède…) | Données européennes pour **pré-entraîner** des modèles sur plus de données | via GBIF pour la plupart ; Mushroom Observer en direct | variables | ✅ (via GBIF) |
| **Placettes de suivi quantitatif** (présence/absence, kg/ha) | CTFC Catalogne : 98 à 131 placettes suivies chaque semaine depuis 1997 ; WSL Suisse (La Chanéaz) ; Castilla y León (Micodata) ; Bielefeld (2015–2024) | publications, données sur demande | à négocier | — |
| **Retours des utilisateurs** de l'application | « trouvé / rien trouvé » + effort (durée, zone) : **seule source d'absences à grande échelle** | à construire | consentement RGPD | — |

### Pièges constatés dans les données GBIF françaises

Ces problèmes ont été trouvés en analysant les données réelles ; ils faussent un modèle s'ils ne sont pas traités.

1. **Observations synthétiques.** Le jeu « Atlas de la Biodiversité Départementale et des Secteurs Marins » publie des présences par département, **toutes datées du 01/04/2016**. Il crée un faux pic d'avril (21 % des « cèpes des pins », 16 % des « oronges » !). → Exclure ce jeu (`datasetKey 23bab45d-e5c8-43fd-8fc5-6a8668becd16`).
2. **Dates par défaut** au 1er janvier ou au 1er du mois (observations connues seulement à l'année ou au mois). → Exclure les jours = 1 ou exiger une précision au jour. Même filtre que [Capinha et al. 2024](https://doi.org/10.1093/biosci/biae041).
3. **Coordonnées imprécises** : seules ~18 % des observations françaises géolocalisées (190 663 sur 1,08 M) ont une incertitude renseignée et inférieure à 1 km ; pour la plupart des autres, la précision est inconnue, et une partie est placée au centroïde de commune. → Filtrer par incertitude quand elle existe, et travailler à une résolution compatible (≥ 1 km) pour l'apprentissage.
4. **Doublons** entre plateformes (INPN Espèces, iNaturalist, associations). → Dédupliquer par espèce × lieu arrondi × date.
5. **Intervalles de dates** (`2019-10-12/2019-10-13`). → Exclure ou prendre le milieu.
6. **Confusions taxonomiques** (cèpes entre eux ; taxonomie des morilles instable). → Modéliser par groupes (« cèpes », « morilles ») au moins au début.
7. **Absences codées** (`occurrenceStatus = ABSENT`) dans certains jeux. → Filtrer `PRESENT`.

## 2.2 Météo passée, présente et prévue

| Source | Contenu | Résolution / période | Accès | Licence | Test |
|---|---|---|---|---|---|
| **Météo-France SIM2** (Safran-Isba-Modcou) | précipitations liquides/solides, températures, ETP, **indice d'humidité des sols (SWI)**, drainage… | maille 8 km (8 981 mailles), quotidien depuis 1958, mise à jour J-1 | [data.gouv.fr « Données SIM »](https://www.data.gouv.fr/datasets/meteo-france-donnees-sim) / meteo.data.gouv.fr | Licence Ouverte Etalab 2.0 (commercial autorisé) | ❌ (data.gouv.fr non joignable depuis l'environnement) |
| **Météo-France COMEPHORE** | lame d'eau radar + pluviomètres | **1 km, horaire**, depuis 1997 ; publié mensuellement (M-2) | [data.gouv.fr « Réanalyses Coméphore »](https://www.data.gouv.fr/datasets/reanalyses-comephore/) | Licence Ouverte | ❌ (idem) |
| ANTILOPE (Météo-France) | lame d'eau temps réel 1 km | temps réel | commercial | payant | — |
| Météo-France stations, AROME (1,3–2,5 km), ARPEGE | observations, prévisions J+2 à J+4 | | portail-api.meteofrance.fr ou via Open-Meteo | Licence Ouverte | ✅ (via Open-Meteo) |
| **ERA5-Land** (Copernicus C3S) | réanalyse : humidité du sol **4 couches** (0–7, 7–28, 28–100, 100–255 cm), température du sol, pluie, ETP… | 0,1° (~9–11 km), horaire, depuis 1950 | CDS (compte gratuit) ou Open-Meteo | licence Copernicus : **usage commercial autorisé** avec attribution | ✅ (via Open-Meteo) |
| **E-OBS** v30.0e (Copernicus / ECA&D) | pluie, températures, humidité, rayonnement à partir des stations | 0,1°, quotidien, 1950 → 06/2024 | téléchargement direct (fichiers NetCDF de 0,3 à 0,8 Go par variable sur 2011–2024) | **non commerciale uniquement** (recherche, enseignement) | ✅ (utilisé pour l'étude de faisabilité) |
| CERRA | réanalyse européenne 5,5 km | 1984–2021 | CDS / Open-Meteo | Copernicus | — |
| **[Open-Meteo](https://open-meteo.com/)** | API unifiée : archives (ERA5, ERA5-Land, CERRA, IFS 9 km), prévisions (ECMWF, Météo-France, DWD…) | dépend du modèle | REST sans clé | **gratuit = non commercial** (600 appels/min, 10 000/jour, 300 000/mois) ; offres commerciales à partir de 1 M d'appels/mois (l'historique est inclus à partir de l'offre « Professional ») ; serveur auto-hébergeable (open source) | ✅ |
| **CLMS Soil Water Index** (Copernicus Land) | humidité du sol par satellite (Sentinel-1 + ASCAT) | **1 km, quotidien**, Europe, depuis 2015 (v2 depuis 07/2025) | Copernicus Data Space | Copernicus | non testé |
| SMAP L4, ESA CCI Soil Moisture | humidité du sol satellite | 9 km / 25 km | NASA / ESA | ouvertes | non testé |

**Choix recommandé :**
- *Prototype* : Open-Meteo (archives ERA5-Land + prévisions), simple et rapide.
- *Production en France* : **SIM2** (humidité du sol modélisée par Météo-France, 8 km, depuis 1958) + **COMEPHORE** (pluie 1 km, cruciale car les orages sont très localisés) + **AROME/ARPEGE** pour les prévisions ; ERA5-Land pour l'Europe et la cohérence historique. Toutes ces sources autorisent un usage commercial.
- *E-OBS* : réservé à la recherche (licence).

## 2.3 Arbres et forêts (hôtes)

| Source | Contenu | Résolution | Accès | Licence | Test |
|---|---|---|---|---|---|
| **IGN BD Forêt V2** | polygones ≥ 0,5 ha, nomenclature de 32 postes ; essence dominante si peuplement pur (≥ 75 %) ; photo-interprétation 2007–2018 | vecteur | WFS Géoplateforme `LANDCOVER.FORESTINVENTORY.V2:formation_vegetale` ; téléchargement par département | Licence Ouverte | ✅ (attributs : `code_tfv`, `tfv`, `tfv_g11`, `essence`, ex. « Forêt fermée de chênes décidus purs ») |
| IGN BD Forêt V3 (en cours) | des couches « MASQUE-FORETV3 » apparaissent déjà dans le catalogue WFS | — | Géoplateforme | Licence Ouverte | ✅ (catalogue) |
| **IGN Inventaire forestier national** (placettes) | essences, dendrométrie, âge, sol, flore par placette | points (coordonnées publiées au centre de la maille de 1 km, jusqu'à ~700 m d'écart) | inventaire-forestier.ign.fr | Licence Ouverte | non testé |
| **Bonannella et al. 2022** (EcoDataCube) | probabilité de présence de **16 essences** européennes (dont hêtre, chênes pédonculé/vert/liège, châtaignier, épicéa, sapin, pins sylvestre/noir/d'Alep/pignon) | **30 m**, 2000–2020 | [PeerJ](https://doi.org/10.7717/peerj.13728), OpenGeoHub | CC-BY | non testé |
| JRC European Atlas of Forest Tree Species | probabilité relative de présence (RPP) par essence | 1 km | JRC Data Catalogue | ouverte | non testé |
| [Giannetti et al. 2026](https://essd.copernicus.org/articles/18/6435/2026/) | 14 types forestiers européens | 100 m | Zenodo | CC-BY | non testé |
| Copernicus HRL Forest Type / Dominant Leaf Type | feuillus / conifères | 10 m | Copernicus Land | ouverte | non testé |
| CORINE Land Cover, Theia OSO, ESA WorldCover | occupation du sol (forêts, prairies, vergers…) | 100 m / 10 m / 10 m | | ouvertes | partiel (CORINE DOM visible dans le WFS IGN) |
| **IGN LiDAR HD** | hauteur de canopée, structure du peuplement | ~1 m | Géoplateforme | Licence Ouverte | non testé |
| IGN BD TOPO `foret_publique` | forêts domaniales et communales | vecteur | WFS | Licence Ouverte | ✅ (catalogue) |

**Stratégie recommandée :** BD Forêt V2 comme couche principale (essence dominante), enrichie par les cartes de probabilité d'essences à 30 m pour les mélanges, et par les placettes IFN pour apprendre les associations hôte–espèce. Les forêts publiques servent aussi à l'aspect réglementaire (dans les forêts relevant du régime forestier, la cueillette est présumée autorisée jusqu'à 5 L sauf réglementation contraire, cf. [chapitre 6](06-architecture-et-feuille-de-route.md#64-risques-éthique-et-réglementation)).

## 2.4 Sols et géologie

| Source | Contenu | Résolution | Accès | Licence | Test |
|---|---|---|---|---|---|
| **SoilGrids 2.0** (ISRIC) | pH, carbone, texture, densité, CEC… sur 6 profondeurs, avec incertitude | 250 m, monde | API REST `rest.isric.org` / fichiers COG | CC-BY 4.0 | ✅ |
| LUCAS topsoil (JRC/ESDAC) | pH, carbonates, texture | ~500 m, Europe | ESDAC | ouverte (inscription) | non testé |
| GisSol (France) | BDGSF 1/1 000 000, RMQS, BDAT, réserve utile | variable | gissol.fr | ouvertes | non testé |
| BRGM BD Charm-50 | géologie 1/50 000 → substrat **calcaire / siliceux** (décisif pour morilles, lactaires…) | vecteur | InfoTerre | Licence Ouverte | non testé |

## 2.5 Relief

IGN **RGE ALTI** (1–5 m) ou BD ALTI (25 m), Copernicus DEM GLO-30 → altitude, pente, exposition, indice topographique d'humidité (TWI), rayonnement potentiel. Indispensable pour corriger la température (gradient ≈ -0,65 °C/100 m) d'une maille météo de 8–11 km vers la parcelle.

## 2.6 Perturbations

- Incendies : EFFIS (UE) et BDIFF (France) → morilles « de feu » au printemps suivant.
- Coupes et dépérissements : cartes de perturbations forestières par satellite (Landsat/Sentinel-2), par ex. Senf & Seidl 2021 pour l'Europe.

## 2.7 Résumé : ce qu'il faut pour un prototype France

| Brique | Source prototype | Source production |
|---|---|---|
| Observations | GBIF (filtré) | GBIF + OpenObs + partenariats + retours utilisateurs |
| Météo passée | Open-Meteo (ERA5-Land) | SIM2 + COMEPHORE (+ ERA5-Land) |
| Prévisions | Open-Meteo | AROME/ARPEGE (Météo-France) |
| Hôtes | BD Forêt V2 | BD Forêt V2/V3 + essences 30 m + IFN |
| Sol | SoilGrids | SoilGrids + BRGM + GisSol |
| Relief | Copernicus DEM | RGE ALTI + LiDAR HD |

[Chapitre suivant : méthodes de modélisation →](03-methodes-de-modelisation.md)
