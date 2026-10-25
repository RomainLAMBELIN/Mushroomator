# 4. L'existant : services publics, recherche appliquée et concurrence

[← Retour au sommaire](README.md)

Informations relevées le 24/10/2026 sur les sites des services (déclarations des éditeurs, non vérifiées sauf mention).

## 4.1 Services publics et recherche appliquée

| Service | Pays | Méthode déclarée | Points à retenir |
|---|---|---|---|
| **Carte de probabilité de pousse du ČHMÚ** (institut hydrométéorologique tchèque) | Tchéquie | saturation du sol par les pluies des **30 derniers jours** + température moyenne des **7 derniers jours** + **coefficient saisonnier** ; 5 niveaux ; espèces mycorhiziennes ; conçue avec la Société mycologique tchèque ; mise à jour quotidienne ; calcul lancé seulement quand des mycologues confirment des pousses sur le terrain ([Seznam Zprávy](https://www.seznamzpravy.cz/clanek/domaci-rostou-meteorologove-zacali-zverejnovat-mapu-pravdepodobneho-rustu-hub-252787)) | preuve qu'un **modèle simple et explicable** suffit pour un service national ; les médias en relaient les limites (« c'est une affaire locale ») |
| **Micodata** (Junta de Castilla y León, CIF Valonsadero puis Cesefor) | Espagne | production hebdomadaire estimée pour les principales espèces à partir de variables écologiques et édapho-climatiques, de la littérature et d'avis d'experts ; visualiseur cartographique ([rapport 2013](https://www.agronewscastillayleon.com/wp-content/uploads/2022/06/informe_balance_produccion_1er_semestre_2013_y_prediccion_otono_2013.pdf)) | données forestières anciennes (3ᵉ inventaire forestier national, 1997–2007) jugées limitantes |
| **CTFC / Université de Lleida** | Catalogne | 98 à 131 placettes permanentes de 10 × 10 m relevées chaque semaine depuis 1997 ; modèles random forest ; cartes à 1 km ; productivité moyenne de référence 65 kg/ha ([Morera et al. 2021](https://doi.org/10.1186/s40663-021-00297-w), [2022](https://doi.org/10.1016/j.agrformet.2022.108918), [2024](https://doi.org/10.1016/j.ecoinf.2024.102557)) | la référence scientifique en Europe ; **partenaire scientifique potentiel** |
| **Biopterre / MAPAQ** (matsutake) | Québec | règles : choc thermique + réserve utile ≥ 70 % + 5–20 °C ; habitat validé par télédétection dans 64 % puis 83 % des cas (2013) | exemple de règles expertes pour une espèce |
| **IMGW** | Pologne | pas de carte « champignons », mais une **prévision d'humidité du sol à 7 jours** (7–28 et 28–100 cm) par IA, très suivie par les cueilleurs ([agrometeo.imgw.pl](https://agrometeo.imgw.pl/prognoza_wilgotnosci_gleby)) | l'humidité du sol prévue est en soi un produit utile |
| **3BMeteo Funghi** | Italie | prévisions « expérimentales » de pousse jour par jour et par commune | grand public, méthode non décrite |

## 4.2 Applications commerciales (France et Europe)

| Application | Couverture | Espèces | Méthode et données déclarées | Validation publiée | Modèle économique |
|---|---|---|---|---|---|
| **[Boletik](https://boletik.fr/)** (Terralab Agritech) | France | cèpes (4 espèces), girolle, pied-de-mouton ; sanguin et morille « en calage » | sol, pluie, forêt, altitude ; un modèle par espèce ; zones probables dans un rayon de 5–10 km ; score 0–100 en 5 classes | partielle : dans la classe 85+, « environ 2 fois plus de cèpes » que dans les autres coins à champignons forestiers, sur 1 427 observations GBIF ; validation du créneau temporel « en cours » | gratuit en 2026, puis « Pass saison » à 9,99 €/an ; coins chiffrés sur l'appareil ; retours « trouvé / rien » optionnels |
| **[Mycora](https://www.mycora.fr/)** | France | cèpe, girolle, morille… | température, humidité, pluie, type et pH du sol, essences ; sources citées : NASA, JRC, Copernicus, Open-Meteo, ISRIC | aucune | compte obligatoire, abonnement (Stripe) |
| **[Champiscope](https://champiscope.fr/)** | toutes les communes de métropole | 4 bolets (+ guides d'espèces) | pluies observées sur 21 et 30 jours + prévision 7 jours (Météo-France, ECMWF) ; épisode de 15–25 mm, premiers sporophores ~10 jours après, pic à 2–3 semaines ; score 0–100 | aucune ; fonction communautaire « le score avait-il vu juste ? » | gratuit + « Champiscope+ » ; liens affiliés |
| **[The Mycologist](https://themycologist.app/)** | France (démo : Doubs) | cèpe, girolle, morille | « plus de 40 données » : forêts, géologie, relief, altitude, essences, sol, pH + pluie, températures, humidité du sol ; probabilité de présence par secteur + indice de pousse quotidien | aucune | abonnement par zone |
| **[Atlas des champignons](https://www.atlas-des-champignons.com/meteo/)** | France | non spécifique | indice de pousse à 7 jours à partir des pluies récentes et des températures | aucune | site de contenu |
| **[ShroomCast](https://shroomcast.net/)** | 16 pays dont la France | 14 espèces | **168 modèles d'apprentissage** (14 espèces × 12 groupes climatiques), météo des 3 dernières semaines, sol, forêt, 3,1 M d'observations ; prévision à 14 jours ; cartes par bois | aucune (« backed by science » sans preuve) | freemium (4 espèces gratuites) |
| **[Waldschatzfinder](https://waldschatzfinder.de/?lang=en)** | Europe (12 langues) | plus de 30 espèces + plantes | modèle de calcul expert développé sur ~12 ans (pas d'IA) : 90 jours d'historique météo + 10 jours de prévision, radar, sol, type de forêt, essences, altitude | « vérifié en continu sur des trouvailles réelles », sans métriques | gratuit, sans publicité, dons |

## 4.3 Lecture stratégique

**Le marché existe et il est encombré.** Au moins sept services visent déjà le cueilleur français, dont plusieurs lancés en 2025–2026. Développer « une carte de pousse de plus » n'a de sens que si elle est **nettement meilleure** et **le prouve**.

Hormis Boletik, qui publie depuis octobre 2026 une page de mesures honnête mais limitée au cèpe ([section 4.4](#44-ce-que-montrent-leurs-sites-analyse-du-25102026)), aucun service ne publie :
- de **validation rigoureuse** (AUC, enrichissement, calibration, rejeu de saisons passées) ;
- de **probabilité calibrée** avec incertitude (tous affichent un score 0–100 arbitraire) ;
- de **méthode documentée** (seuls le ČHMÚ et Champiscope donnent quelques règles).

### Axes de différenciation possibles

1. **Rigueur scientifique visible** : méthode publiée, rapport de validation par espèce et par saison mis à jour chaque année, comparaison à des références simples. Possibilité de publication scientifique (la méthode « niche phénologique » appliquée à la France est encore peu exploitée).
2. **Probabilités calibrées et incertitude** grâce aux retours terrain (« trouvé / rien » + temps passé) : transformer l'indice en vraie probabilité, ce qu'aucun concurrent ne fait.
3. **Explicabilité** : « pourquoi ce score ? » → *pluie sur 30 j : 85 mm ✔ · température 14 j : 12 °C ✔ · hôte : hêtraie-chênaie ✔ · sol acide ✔ · gel annoncé jeudi ✘*.
4. **Finesse de l'habitat** : BD Forêt + essences à 30 m + LiDAR HD + pH, là où beaucoup se limitent à « forêt / pas forêt ».
5. **Sécurité intégrée** : chaque espèce affichée avec ses confusions dangereuses ; aucune aide à l'identification par photo ; rappel ANSES.
6. **Éthique et réglementation** : affichage forêts publiques / privées, rappel des quotas, pas de partage de coins, agrégation des retours.
7. **Ouverture** : données et code de recherche ouverts, partenariats (sociétés mycologiques, CTFC, ONF), ce qui peut aussi ouvrir l'accès à des données d'absence.

## 4.4 Ce que montrent leurs sites (analyse du 25/10/2026)

Analyse des pages publiques, des requêtes faites par leurs applications et des réponses de leurs interfaces publiques, une visite par site, sans compte ni contournement.

| Service | Ce qui a été observé |
|---|---|
| **Champiscope** | Score météo à règles, par secteur d'une grille couvrant la France. L'interface de la page (`/api/pousse-report?lat=…&lon=…`) renvoie pour chaque jour un score 0–100, un palier (« Pousse probable », « Fenêtre idéale ») et quatre facteurs : **réserve en eau de la litière** (seau de 40 mm), **pluie déclenchante et délai depuis** (« 101 mm il y a 16 j, latence idéale »), **température moyenne**, **saison** ; plus 30 jours de pluie et 7 jours d'historique ; prévision au-delà de 1 jour réservée aux comptes. Aucune couche d'habitat : le site refuse explicitement de montrer des coins (« des secteurs et des villes, pas des parcelles ni des sous-bois »). |
| **Waldschatzfinder** | Calcul côté serveur (`process.php?ort=lat,lon`). La page de résultat affiche une « chance du jour » en pourcentage et quatre facteurs à seuils : **pluie sur 14 jours** (bonne dès ~40 mm), **jours depuis la dernière forte pluie** (idéal de 5 à 16), **maximum journalier moyen sur 7 jours** (idéal de 12 à 22 °C), **humidité de l'air sur 7 jours** (bonne dès 80 %). La carte des « hotspots » (sol, essences) est réservée aux comptes. |
| **Boletik** | Page de mesures publique ([boletik.fr/comment-on-mesure](https://boletik.fr/comment-on-mesure), 14/10/2026), sur 1 427 observations GBIF de cèpes : face aux autres champignons de forêt, la meilleure classe d'habitat (note ≥ 85) compte **2,1 fois plus de cèpes**, mais seuls 17 points de comparaison y tombent ; indice de Boyce 0,90. Pour le jour : calendrier seul 73/100, score météo 64/100, les deux 74/100 ; au sein d'un même mois, 54/100. Une pluie de 30 mm ou plus 10 à 30 jours avant précède 48 % des jours de trouvaille contre 39 % des autres jours ; l'humidité du sol en surface ne distingue rien. Données : BD Forêt, OCS GE, relief, géologie BRGM, CORINE, Open-Meteo. L'application affiche une couche forêt précalculée en images (PMTiles, zooms 4 à 9, pixels de 200 à 300 m) sur fond IGN. |
| **Mycora** | Carte réservée aux comptes ; sources citées sur la page d'accueil : NASA, Copernicus, JRC, ISRIC (sols), Open-Meteo. |
| **ShroomCast, The Mycologist** | Derrière un captcha ou un abonnement : rien de plus que leurs déclarations ([section 4.2](#42-applications-commerciales-france-et-europe)). |
| **Atlas des champignons, 3BMeteo** | Indices calculés côté serveur et livrés dans la page, sans détail de méthode. |

**Lecture**

1. **Le « quand » repose partout sur des règles simples** : une pluie déclenchante (30 à 40 mm), un délai de 5 à 30 jours, une température, la saison. Notre modèle apprend ces mêmes relations sur les observations au lieu de les fixer, et les valide sur des années non vues.
2. **Personne ne situe les coins à fine échelle** : Champiscope s'y refuse, Waldschatzfinder et Boletik raisonnent par secteur ou à environ 250 m. Le meilleur résultat publié, celui de Boletik, reste modeste et fragile (2,1 fois plus de cèpes dans la meilleure classe, sur 17 points de comparaison).
3. **Idées à reprendre** : tester un seau de litière de faible capacité (40 mm) comme variable de déclenchement ; afficher explicitement le délai depuis la pluie déclenchante, très parlant pour l'utilisateur ; un libellé de saison ; des retours « trouvé / rien » anonymes et désactivés par défaut.
4. **Différenciation** : l'échelle du coin (LiDAR HD, relief fin), qui est l'objet du [chapitre 8](08-identifier-les-coins.md).

[Chapitre suivant : étude de faisabilité →](05-etude-de-faisabilite.md)
