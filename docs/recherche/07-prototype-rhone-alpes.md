# 7. Prototype : Rhône-Alpes et alentours

[← Retour au sommaire](README.md)

Premier prototype complet pour un usage personnel et gratuit : carte web (utilisable sur téléphone), 9 espèces, zone allant du Massif central aux Alpes (3,3° E à 7,3° E, 43,9° N à 46,8° N, 21 départements français couverts par la BD Forêt). Mode d'emploi : [README du dépôt](../../README.md).

## 7.1 Ce que fait l'application

- **Carte de chaleur** à ~175 m de résolution (pixels Web Mercator de 250 m), pour le jour choisi entre **J-7 et J+7**.
- Trois couches : **Indice** = habitat × conditions ; **Habitat** (arbres-hôtes, altitude, pH) ; **Conditions** (météo comparée aux jours habituels de la saison).
- **Frise des 15 jours** : conditions moyennes en habitat favorable, pour repérer le meilleur jour.
- **Carnet de sorties et coins semblables** : sorties notées sur le téléphone (trouvé / rien trouvé, indice du jour), export et import ; vue des peuplements qui ressemblent aux coins productifs ([chapitre 8](08-identifier-les-coins.md#88-la-méthode-retenue)).
- **Recherche de lieux** : géocodage IGN Géoplateforme (communes, lieux-dits, sommets, cols, forêts, lacs, adresses), limité aux départements cartographiés et classé pour la cueillette (lieux naturels avant les rues) ; les coordonnées GPS sont acceptées, même hors ligne.
- **Clic sur la carte** : décomposition complète du score (essence dominante, altitude, pH, effet de chaque variable météo) et graphiques de pluie et de température du secteur (45 jours passés + prévision).
- Sécurité : avertissement au premier lancement, confusions dangereuses par espèce, rappel des règles de cueillette.
- **Sur téléphone, sans installation** : site statique publié sur GitHub Pages et mis à jour chaque matin par GitHub Actions (tests, météo, déploiement).
- Hors-ligne : l'application, les dernières données et les fonds de carte déjà consultés (jusqu'à 1 500 tuiles) restent disponibles sans réseau. Les jours sont nommés d'après la date du téléphone, avec une mention quand la météo enregistrée date d'un jour précédent.

## 7.2 Architecture

| Élément | Rôle | Rafraîchissement |
|---|---|---|
| `assets/regions/rhone-alpes/` | essence dominante (BD Forêt V2 rasterisée à 50 m puis agrégée), couverture forestière, altitude (Copernicus DEM, pas de 10 m), pH 0–30 cm (SoilGrids) ; 5,3 Mo | une fois (`python -m mushroomator layers`) |
| `assets/models/*.json` | modèles de déclenchement exportés en tables (une courbe par variable) | une fois par an (`train`) |
| `assets/validation/rhone-alpes.json` | validation de l'habitat, tables d'hôtes calibrées, rejeu des saisons | après chaque entraînement (`validate`) |
| `site/data/rhone-alpes/weather.json` | météo de 352 points (grille de 0,2°) : 92 jours passés + 8 jours de prévision Open-Meteo, variables du modèle ; ~300 Ko (~60 Ko compressés) | chaque jour (`update`, lancé par GitHub Actions) |
| `site/sw.js` | cache hors-ligne : tous les fichiers du site (~4,4 Mo) enregistrés après la première visite ; une nouvelle version est téléchargée en arrière-plan puis utilisée à l'ouverture suivante ; météo : réseau d'abord, dernière météo enregistrée si le réseau ne répond pas en 4 s | version recalculée à chaque génération du site (hors météo) |
| `web/` | application (Leaflet, calcul de l'indice dans le navigateur) | — |

Le calcul de l'indice se fait **dans le navigateur** : la carte entière (3,3 M de pixels) est recalculée en ~0,15 s. La température est ramenée au niveau de la mer sur la grille météo puis redescendue à l'altitude de chaque pixel (−0,65 °C/100 m) : en montagne, deux versants voisins n'ont donc pas les mêmes conditions. Un test automatique vérifie que le calcul JavaScript donne les mêmes valeurs que le calcul Python (écart < 0,002).

## 7.3 Modèle de déclenchement

- **Données** : 9 espèces, observations GBIF datées de France et de Suisse (2011–2024), filtrées comme au [chapitre 2](02-sources-de-donnees.md#pièges-constatés-dans-les-données-gbif-françaises) ; météo E-OBS (0,1°).
- **Plan** : 10 dates témoins par observation au même endroit, sur toute l'année (le modèle apprend donc aussi la saisonnalité).
- **Altitude** : la température E-OBS de la maille est corrigée vers l'altitude réelle du lieu d'observation (relief Copernicus).
- **Modèle additif** : une spline par variable puis une régression logistique. Variables : jour de l'année, température moyenne sur 14 jours, pluie sur 30 jours, pluie tombée il y a 1 à 3 semaines, réserve en eau du sol (modèle « seau »).
- Ce modèle simple fait aussi bien ou mieux que les arbres boostés de l'étude de faisabilité (cèpe 0,77 contre 0,76 ; trompette 0,75 contre 0,72 ; girolle 0,68 contre 0,65 sur le même jeu), tout en donnant l'effet de chaque variable.
- **Échelle** : le score est converti en percentile des jours habituels de la saison (100 = parmi les meilleurs jours).
- **Cohérence des sources météo** : sur 12 points de la région en 2023–2024, la température Open-Meteo et la température E-OBS (après correction d'altitude) diffèrent de −0,08 °C en moyenne (corrélation de 0,98 à 0,996). Pour la pluie, le rapport médian est de 1,04, sans biais global, avec de fortes variations locales (0,7 à 1,8 sur les sommets).

## 7.4 Modèle d'habitat

`habitat = hôte(essence BD Forêt) × altitude × pH`. Les tables ont été fixées a priori d'après la littérature, puis **confrontées aux observations régionales** : 4 967 observations précises de 30 autres champignons forestiers servent de « groupe cible » (même effort d'observation).

- **Calibration des hôtes** : a priori × (rapport de sélection observé)^0,5, avec 5 observations fictives pour amortir les petits effectifs. Elle n'est retenue que si elle améliore l'AUC en validation croisée à 5 blocs. Elle l'est pour 7 espèces sur 9.
- **Ce que les données ont appris** : en Rhône-Alpes, la girolle est surtout notée sous châtaigniers et chênes méditerranéens (Ardèche, Cévennes) plutôt que sous hêtre. Elle ne se trouve pas sur des sols plus acides que les autres champignons forestiers ; sa préférence de pH a donc été retirée. Les morilles et le lactaire délicieux préfèrent nettement les sols calcaires (AUC du seul facteur pH : 0,74). Les morilles sont souvent signalées hors forêt (vergers, jardins, berges : 16 % de leurs observations contre 5 %), un habitat que la carte ne couvre pas.

## 7.5 Résultats de validation

| Espèce | Obs. (FR + CH) | Saison | Conditions en saison : saison seule → avec météo | Idem en Rhône-Alpes | Habitat vs autres champignons | Rejeu : jour trouvé vs autres jours | Rejeu : vs autres champignons |
|---|---:|---|---:|---:|---:|---:|---:|
| Cèpe de Bordeaux | 2 058 | 18/06–22/11 | 0,66 → **0,73** | 0,75 | 0,50 | 0,89 | 0,71 |
| Girolle | 1 577 | 22/05–13/11 | 0,62 → **0,69** | 0,67 | 0,51 | 0,79 | 0,62 |
| Trompette de la mort | 712 | 15/07–07/12 | 0,64 → **0,71** | 0,76 | 0,63 | — | — |
| Chanterelle en tube | 991 | 17/01–22/12 | 0,82 → **0,85** | 0,87 | 0,59 | 0,91 | 0,75 |
| Pied de mouton | 1 444 | 25/02–10/12 | 0,79 → **0,83** | 0,83 | 0,47 | 0,84 | 0,68 |
| Morilles | 964 | 14/03–05/06 | 0,65 → **0,68** | 0,67 | 0,56 | 0,89 | 0,94 |
| Hygrophore de mars | 276 | 13/02–28/05 | 0,57 → **0,66** | 0,67 | — | — | — |
| Lactaire délicieux | 448 | 25/07–05/12 | 0,68 → **0,75** | 0,78 | 0,58 | — | — |
| Oronge | 233 | 23/06–13/11 | 0,61 → **0,78** | 0,80 | 0,87 | — | — |

Lecture (AUC : 0,5 = hasard, 1 = parfait) :
- **Conditions** : distinguer les jours d'observation des autres jours de la saison, sur des années non vues à l'entraînement. La météo apporte de +0,03 (morilles) à +0,17 (oronge).
- **Habitat** : distinguer les lieux d'observation de l'espèce de ceux d'autres champignons forestiers. L'habitat situe très bien l'oronge (0,87) et assez bien la trompette, la chanterelle en tube et le lactaire (≈ 0,6). Pour le cèpe, la girolle et le pied de mouton, il ne fait pas mieux que « en forêt » : la BD Forêt à ~200 m ne capte pas ce qui distingue leurs coins.
- **Rejeu** (2011 à mi-2024, Rhône-Alpes, indice calculé exactement comme dans l'application) : à lieu fixe, l'indice du jour de l'observation dépasse celui d'un jour quelconque de l'année dans 79 à 91 % des cas. Face aux observations d'autres champignons, celles de l'espèce sont mieux classées dans 62 à 94 % des cas. « — » : moins de 20 observations précises dans la région.

## 7.6 Limites connues

- **Indice relatif**, pas une probabilité : il faudra des retours « trouvé / rien trouvé » pour le calibrer.
- Habitat **limité aux formations de la BD Forêt** (forêts, landes, pelouses naturelles) : vergers, jardins et prairies agricoles ne sont pas couverts, ce qui pénalise les morilles et les espèces de prairie. La Suisse et l'Italie ne sont pas couvertes non plus.
- Pas de facteur de climat moyen dans l'habitat : pour une espèce thermophile comme l'oronge, la couche Habitat s'étend aussi aux chênaies plus fraîches du nord de la zone ; seule la couche Conditions en tient compte.
- Pluie interpolée depuis une grille de 0,2° (~20 km) : les orages locaux sont lissés.
- Entraînement sur E-OBS, application sur Open-Meteo : écart vérifié faible en température, plus variable pour la pluie.
- Petits effectifs régionaux pour la validation de certaines espèces (hygrophore de mars : 6 observations précises).

## 7.7 Prochaines étapes possibles

La priorité est désormais de mieux situer les coins (le *où*) : voir le [chapitre 8](08-identifier-les-coins.md).

1. Formulaire « trouvé / rien trouvé » enregistré sur le téléphone, pour mesurer la fiabilité réelle et calibrer l'indice.
2. Pluie radar COMEPHORE (1 km) et humidité du sol SIM2 de Météo-France pour l'historique.
3. Couche « hors forêt » pour les morilles (vergers, ripisylves, CORINE/OSO).
4. Espèces de printemps et de prairie (mousseron de la Saint-Georges, coulemelle).
5. Prévision à 14 jours (ensemble ECMWF) avec incertitude.

[Chapitre 8 : identifier les coins →](08-identifier-les-coins.md)
