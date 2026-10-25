# 8. Objectif : identifier les coins à champignons

[← Retour au sommaire](README.md)

> **Objectif du projet : un outil qui aide à identifier les coins à champignons**, c'est-à-dire dire *où* chercher à l'échelle du coin (quelques dizaines de mètres), et *quand* y aller.

## 8.1 Où en est-on ?

| | Fiabilité actuelle ([chapitre 7](07-prototype-rhone-alpes.md#75-résultats-de-validation)) |
|---|---|
| **Quand** (météo des semaines précédentes) | correcte : AUC en saison de 0,66 à 0,85 sur des années non vues ; la météo améliore toujours le calendrier seul |
| **Où** (habitat) | faible : 0,50 pour le cèpe, 0,51 pour la girolle, 0,47 pour le pied de mouton, autour de 0,6 pour la trompette, la chanterelle en tube et le lactaire ; seule l'oronge est bien située (0,87) |

L'habitat actuel ne voit que l'essence dominante du peuplement (BD Forêt, polygones d'au moins 0,5 ha, regroupés en pixels de 250 m), un pH à 250 m et un relief à 90 m. Or un coin se joue entre 10 et 100 m : tel versant, telle combe, telle parcelle de vieux hêtres plutôt que la plantation voisine.

## 8.2 Ce qui fait un coin, et comment le voir

| Facteur | Pourquoi il compte | Comment le voir à fine échelle |
|---|---|---|
| **Âge, densité et structure du peuplement** | la production des espèces mycorhiziennes dépend de l'âge du peuplement et de sa densité (surface terrière), avec des optimums propres à chaque espèce : jeunes pinèdes pour le lactaire délicieux, peuplements plus mûrs pour le cèpe (Martínez de Aragón et al. 2007 ; Bonet et al. 2010 ; Tahvanainen et al. 2016 ; synthèse de Tomao et al. 2017) | **hauteur de la végétation LiDAR HD** (MNH, 1 m) : âge approché, trouées, lisières, peuplement clair ou fermé ; densité des points LiDAR au-dessus du sol pour le sous-bois |
| **Humidité du sol à petite échelle** | combes, bas de versant et replats restent humides quand les crêtes sèchent | indice d'humidité topographique, pente et courbure calculés sur le **relief à 1–5 m** (RGE ALTI, MNT LiDAR HD) |
| **Exposition et microclimat** | versants nord plus frais et humides, versants sud plus précoces ; espèces thermophiles comme l'oronge | orientation et rayonnement solaire (relief fin) ; **température sous couvert à 25 m** pour l'Europe (ForestTemp, Haesen et al. 2021) |
| **Roche-mère** | calcaire ou silice : préférence nette de certaines espèces (morilles et lactaire délicieux sur calcaire, [chapitre 7](07-prototype-rhone-alpes.md#74-modèle-dhabitat)) | carte géologique du BRGM au 1/50 000, bien plus fine que SoilGrids (250 m) |
| **Essences mélangées** | la BD Forêt ne donne que l'essence dominante ; un hêtre isolé dans une pessière peut porter des girolles | cartes d'essences issues de Sentinel-2 (Bonannella et al. 2022, 30 m) |
| **Perturbations** | une coupe rase supprime les hôtes ; les morilles abondent l'année qui suit un incendie (Larson et al. 2016) | cartes de perturbations forestières (Senf & Seidl 2021, 30 m), contours d'incendies, Sentinel-2 |

Au Danemark, des variables tirées du LiDAR (structure de la végétation, humidité liée au relief) expliquent une part importante de la richesse et de la composition des champignons sur 130 sites (Thers et al. 2017). C'est l'argument le plus direct en faveur du LiDAR pour situer les coins.

## 8.3 Données vérifiées le 25/10/2026

- **LiDAR HD de l'IGN** : hauteur de végétation (MNH), terrain (MNT) et surface (MNS) sont diffusés par la Géoplateforme en valeurs brutes (WMS, `image/x-bil;bits=32`). Extrait test de 2,4 × 2,2 km autour du Charmant Som (Chartreuse) : données complètes, hauteur médiane de la végétation 6,9 m, 21 m pour les 10 % les plus hauts. La couverture est donc disponible dans notre zone, au moins dans ce massif.
- **RGE ALTI haute résolution** (1–5 m) : disponible de la même façon.
- **Géologie du BRGM** : le service rejette les requêtes depuis l'environnement de développement ; à tester depuis une connexion normale.
- **Observations précises** (incertitude déclarée ≤ 50 m, GBIF) : peu nombreuses en France, beaucoup plus en Europe du Nord, grâce aux atlas mycologiques danois, suédois et norvégiens.

| Espèce | France ≤ 50 m | Europe ≤ 50 m |
|---|---:|---:|
| Cèpe de Bordeaux | 342 | 16 417 |
| Girolle | 200 | 15 180 |
| Trompette de la mort | 103 | 3 895 |
| Pied de mouton | 131 | — |
| Chanterelle en tube | 111 | — |
| Morilles | 107 | — |
| Lactaire délicieux | 85 | — |
| Oronge | 50 | 244 |
| Hygrophore de mars | 2 | — |

« — » : non compté. Beaucoup d'observations françaises n'indiquent pas leur précision ; la base nationale fongique (Gautier et al. 2022) en contient sans doute davantage de précises, mais son accès (OpenObs) n'a pas pu être testé d'ici.

## 8.4 Trois leviers

1. **Voir la forêt à l'échelle du coin.** Une couche habitat à 25 m au lieu de 250 m, avec le LiDAR HD, le relief fin et la géologie, apprise sur les observations précises. Comme la France n'en compte que quelques centaines par espèce, les relations fines peuvent être apprises sur les observations européennes avec des couches disponibles partout (hauteur du couvert à 10 m de Lang et al. 2023, essences, ForestTemp), puis vérifiées en France.
2. **Vos coins et vos sorties.** C'est l'information la plus riche, et elle reste privée sur le téléphone :
   - un **carnet** de sorties (trouvé / rien trouvé, position GPS) ;
   - des **coins semblables** : à partir de vos bons coins, même peu nombreux, la carte montre les endroits voisins qui leur ressemblent (essence, hauteur du peuplement, pente, exposition, altitude, sol) ;
   - après une saison, une **calibration** : vos « rien trouvé » sont les absences qui manquent pour transformer l'indice en probabilité.
3. **Des signaux propres à certaines espèces** : incendies de l'année précédente, ripisylves et vergers pour les morilles (hors BD Forêt : occupation du sol OSO ou BD TOPO) ; jeunes pinèdes pour le lactaire délicieux ; chaleur sous couvert pour l'oronge.

## 8.5 Comment savoir si c'est mieux

- **Critère principal** : AUC de l'habitat face aux observations d'autres champignons forestiers (même effort d'observation), en validation croisée par blocs spatiaux. Point de départ : 0,50 pour le cèpe et la girolle. Objectif : au moins 0,65.
- **Concentration** : part des observations qui tombent dans les 10 % de forêt les mieux notés (10 % = hasard).
- **Sur le terrain** : taux de réussite de vos sorties selon l'indice, une fois le carnet en place.

Attente réaliste : passer de « toute la forêt se vaut » à « ces parcelles d'abord ». Aucune donnée ne montrera l'emplacement exact d'un cèpe : le mycélium est invisible et la fructification reste irrégulière d'une année à l'autre.

## 8.6 Feuille de route

| Étape | Contenu | Décision ou critère |
|---|---|---|
| 1. Expérience | Extraire LiDAR HD et relief fin autour des observations précises françaises et du groupe cible ; comparer l'AUC de l'habitat avec et sans ces variables | **fait le 25/10/2026** : pas de gain pour le cèpe et la girolle ([section 8.7](#87-résultats-des-essais-du-25102026)) |
| 2. Carnet et coins semblables | Dans l'application : sorties notées sur le téléphone, export possible, carte des endroits qui ressemblent à vos coins | **fait le 25/10/2026** (première version : ressemblance par type de peuplement, altitude et pH à 250 m, × conditions du jour ; taux de réussite selon l'indice dès 10 sorties) |
| 3. Habitat à 25 m dans l'application | Tuiles d'habitat précalculées par espèce, chargées à la demande et gardées hors ligne | abandonné tant que les variables fines n'apportent rien (sauf pour les morilles) |
| 4. Apprentissage européen | Si l'étape 1 montre que les variables fines aident mais que les données françaises manquent | sans objet : les variables fines n'aident pas |
| 5. Calibration | Après une saison de sorties notées | indice exprimé en probabilité de trouver |

## 8.7 Résultats des essais du 25/10/2026

**Données** : observations GBIF françaises localisées à 50 m près ou mieux (cèpe 300, girolle 167, pied de mouton 115, morilles 103, chanterelle en tube 99, trompette 96, lactaire délicieux 80, oronge 49) et 10 229 observations de 30 autres champignons forestiers (même effort d'observation). Autour de chaque point : hauteur de végétation LiDAR HD (moyenne, hauteur des grands arbres, hétérogénéité, part de trouées dans des rayons de 10, 25 et 50 m), relief RGE ALTI (pente, exposition, creux et bosses de 25 à 200 m, courbure, indice d'humidité), distance aux cours d'eau (BD TOPO) et type de peuplement BD Forêt au point exact. Validation croisée par blocs spatiaux de 20 km, répétée trois fois. AUC : 0,5 = hasard, 1 = parfait.

| Test | Question posée | Cèpe | Girolle | Trompette | Pied de mouton | Morilles |
|---|---|---:|---:|---:|---:|---:|
| 1. Face aux autres champignons | le micro-habitat de l'espèce diffère-t-il ? (données grossières → + LiDAR et relief) | 0,55 → 0,55 | 0,64 → 0,59 | 0,61 → 0,67 | 0,60 → 0,55 | 0,69 → 0,77 |
| 2. Coin face à son voisinage | le point d'observation se distingue-t-il de points en forêt à 60–400 m, à la même distance d'un chemin ? | 0,50–0,54 | 0,50–0,60 | 0,53–0,60 | ≈ 0,50 | 0,65–0,72 |
| 3. Parcelle face aux forêts alentour | même question avec des points à 0,5–5 km | 0,58–0,59 | 0,55 | 0,62 | 0,58–0,60 | 0,60 |
| 3 bis. Essence au point seule | BD Forêt au point exact, toute la France | 0,58 | 0,48 | 0,60 | 0,64 | — |
| 4. Persistance | une ancienne observation de l'espèce à moins de 500 m annonce-t-elle les suivantes ? | 0 % des 181 trouvailles récentes | 1 % | 1 % | 1 % | 1 % |

Avec les seuls champignons du sol en comparaison (sans les champignons du bois), les conclusions du test 1 sont identiques.

**Lecture**

- Pour le cèpe et la girolle, **aucune donnée publique fine ne distingue le coin** : ni la structure du couvert vue par le LiDAR, ni le relief, ni l'eau, ni l'essence au point. Le critère fixé (≥ 0,65) n'est pas atteint.
- **Les morilles font exception** (0,72 à 0,77) : elles fréquentent des terrains ouverts et remaniés, que la hauteur de végétation LiDAR repère bien.
- À l'échelle des parcelles (0,5–5 km), un signal modeste apparaît (autour de 0,6 ; 0,6 à 0,64 pour l'ensemble des champignons forestiers). Il tient en partie à l'endroit où l'on marche : terrain peu pentu, forêt fermée de grands arbres.
- Les observations publiques précises sont **trop rares pour cartographier des coins connus** : 145 observations précises de cèpes avant 2021 pour toute la France.
- Limites : précision réelle des positions GBIF (≤ 50 m déclarés), biais d'effort des cueilleurs, tables d'hôtes calées sur Rhône-Alpes (la girolle les met en défaut ailleurs).

## 8.8 La méthode retenue

L'information qui fait un coin de cèpes ou de girolles (les arbres un par un, leur âge, le sol, l'histoire du mycélium) n'est dans aucune couche publique. Les concurrents ne font pas mieux : aucun ne situe les coins à fine échelle ([section 4.4](04-existant-et-concurrence.md#44-ce-que-montrent-leurs-sites-analyse-du-25102026)). La méthode satisfaisante s'appuie donc sur vos propres observations, avec l'outil pour les guider et en apprendre :

1. **Prospecter les bons peuplements au bon moment** : habitat par peuplement (essence, altitude, sol) et conditions météo, la partie validée de l'outil.
2. **Noter chaque sortie** dans un carnet privé, gardé sur le téléphone, y compris les sorties où l'on ne trouve rien.
3. **Apprendre de vos sorties** : montrer les peuplements proches qui ressemblent à vos coins productifs, puis, avec assez de sorties notées, la probabilité réelle de trouver selon l'indice.
4. **Afficher les observations publiques précises** à proximité comme indices, en sachant qu'elles sont rares.

Critères de réussite, mesurés sur vos sorties notées : la part de sorties fructueuses augmente avec l'indice, et les coins semblables produisent plus souvent que les autres peuplements prospectés.

## Références de ce chapitre

Bonet et al. 2010 ; Bonannella et al. 2022 ; Gautier et al. 2022 ; Haesen et al. 2021 ; Lang et al. 2023 ; Larson et al. 2016 ; Martínez de Aragón et al. 2007 ; Senf & Seidl 2021 ; Tahvanainen et al. 2016 ; Thers et al. 2017 ; Tomao et al. 2017. Détails dans la [bibliographie](references.md).

[Bibliographie →](references.md)
