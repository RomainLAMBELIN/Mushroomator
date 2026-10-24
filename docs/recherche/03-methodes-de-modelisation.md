# 3. Méthodes de modélisation

[← Retour au sommaire](README.md)

## 3.1 Bien définir ce que l'on prédit

« Probabilité de trouver un cèpe ici aujourd'hui » se décompose en trois termes :

$$
P(\text{trouver}) = \underbrace{P(\text{présent en } x)}_{\text{habitat}} \times \underbrace{P(\text{fructifie le jour } t \mid \text{présent})}_{\text{déclenchement météo}} \times \underbrace{P(\text{repéré} \mid \text{fructifie, effort})}_{\text{détection}}
$$

Le point méthodologique le plus important du dossier : **avec des données de présence seule (GBIF, iNaturalist…), on ne peut estimer qu'une intensité *relative*, pas une probabilité absolue.** La prévalence (combien de placettes contiennent l'espèce) n'est pas identifiable sans données d'absence ([Hastie & Fithian 2013](https://doi.org/10.1111/j.1600-0587.2013.00321.x) ; [Guillera-Arroita et al. 2015](https://doi.org/10.1111/geb.12268)).

Conséquences pour le produit :
- **Afficher un indice relatif** (par ex. « 85ᵉ percentile : meilleur que 85 % des situations de saison ») tant que l'on n'a pas d'absences.
- **Collecter des absences** dès le lancement : chaque sortie « rien trouvé » avec sa durée et sa zone est une donnée précieuse. C'est elle qui permettra ensuite de **calibrer** l'indice en vraie probabilité (§ 3.6).

## 3.2 Approche 0 : règles expertes (référence à battre)

Fonctions d'appartenance (logique floue) par espèce, combinées par produit ou moyenne géométrique :

```
indice(x, t) = f_hôte(essence(x)) · f_sol(pH(x)) · f_saison(jour) · f_pluie(P30(x,t)) · f_temp(T14(x,t)) · f_chaleur(Tmax) · f_gel(...)
```

C'est l'approche des services opérationnels : le **ČHMÚ** (Tchéquie) combine la saturation du sol par les pluies des 30 derniers jours, la température moyenne des 7 derniers jours et un coefficient saisonnier, en 5 classes ; l'outil québécois du matsutake combine choc thermique, réserve utile ≥ 70 % et température 5–20 °C.

- **Pour** : aucune donnée d'entraînement, interprétable, livrable en quelques jours.
- **Contre** : seuils arbitraires, aucune garantie de qualité tant qu'elle n'est pas validée.
- **Usage** : version 0 de l'application **et** référence (baseline) que tout modèle appris doit battre.

## 3.3 Couche « habitat » : modèles de distribution d'espèces (SDM)

Objectif : une carte quasi statique (mise à jour annuelle) de l'aptitude de chaque maille à héberger l'espèce.

### Méthodes

| Famille | Exemples | Commentaire |
|---|---|---|
| Entropie maximale | **MaxEnt** ([Phillips et al. 2017](https://doi.org/10.1111/ecog.03049)), `maxnet`, `elapid` (Python) | la plus utilisée pour les champignons ([Hao et al. 2020](https://doi.org/10.1016/j.fbr.2020.01.002) : revue de 283 études) ; équivalente à un processus ponctuel de Poisson ([Renner et al. 2015](https://doi.org/10.1111/2041-210X.12352)) |
| Arbres boostés | **BRT/GBM**, XGBoost, LightGBM ([Elith et al. 2008](https://doi.org/10.1111/j.1365-2656.2008.01390.x)) | très performants, gèrent interactions et non-linéarités |
| Forêts aléatoires | **RF « down-sampled »** (équilibrée) | 2ᵉ meilleure méthode du banc d'essai de référence, très supérieure aux RF classiques sur des données présence/fond |
| Régressions | GLM pénalisé (lasso), GAM | plus robustes en extrapolation, bonnes pour l'interprétation |
| Ensembles | moyenne de modèles réglés | **meilleure méthode** du banc d'essai |
| Bayésien spatial | INLA / `inlabru` (processus de Cox log-gaussien) | gère l'autocorrélation spatiale et l'incertitude |
| Multi-espèces | HMSC ([Ovaskainen et al. 2017](https://doi.org/10.1111/ele.12757)) | « emprunte » de l'information aux espèces voisines (utile pour les espèces rares) |
| Deep learning | CNN sur imagettes d'environnement ([Deneu et al. 2021](https://doi.org/10.1371/journal.pcbi.1008856)) ; **SINR** ([Cole et al. 2023](https://arxiv.org/abs/2306.02564)) | SINR apprend 47 000 espèces à la fois à partir de présences seules ; pertinent si l'on vise des centaines d'espèces |

Le banc d'essai de référence ([Valavi et al. 2022](https://doi.org/10.1002/ecm.1486), 225 espèces, données d'évaluation indépendantes) conclut : **la meilleure méthode est un ensemble de modèles individuellement réglés** (lasso, GAM, MaxEnt, BRT, RF down-sampled) ; ensuite la **RF down-sampled** ; MaxEnt et BRT restent dans le peloton de tête ; les ensembles `biomod2` avec paramètres par défaut ne font pas mieux qu'un modèle moyen. Autrement dit : **la façon d'ajuster compte plus que l'algorithme.**

### Variables explicatives de l'habitat

- **Hôtes** : essence dominante (BD Forêt), probabilités d'essences à 30 m, proportion feuillus/conifères, âge/hauteur du peuplement (LiDAR HD).
- **Sol** : pH, texture, carbone, réserve utile (SoilGrids, GisSol) ; substrat calcaire/siliceux (BRGM).
- **Climat moyen** : normales 1991–2020 (pluie annuelle et estivale, températures, aridité) issues de SAFRAN/ERA5-Land.
- **Relief** : altitude, exposition, pente, TWI.
- **Contexte** : distance à la lisière, occupation du sol.

### Corriger le biais d'observation (crucial)

Les observations se concentrent près des villes, des sentiers et des sociétés mycologiques actives (FongiBase : 4 foyers d'échantillonnage intense, Méditerranée sous-documentée). Sans correction, le modèle apprend « là où vont les gens ».

1. **Fond « groupe cible »** ([Phillips et al. 2009](https://doi.org/10.1890/07-2153.1)) : tirer les points de fond parmi les observations de *tous* les champignons, qui partagent le même biais d'effort.
2. **Covariables de biais** (distance aux routes et aux villes, densité de population) incluses à l'ajustement puis **fixées à une valeur constante** pour la prédiction.
3. **Amincissement spatial** (une observation par maille).
4. **Modèles intégrés** qui combinent présences opportunistes et inventaires standardisés ([Fithian et al. 2015](https://arxiv.org/abs/1403.7274) ; § 3.6).

## 3.4 Couche « déclenchement » : phénologie pilotée par la météo

Objectif : pour une maille où l'espèce est présente, estimer chaque jour la propension à fructifier, à partir de la météo des semaines précédentes et de la prévision.

### Variables (« feature engineering »)

| Groupe | Variables |
|---|---|
| Pluie cumulée | P1, P3, P7, P14, P21, P30, P45, P60 (mm) |
| Pluie décalée | pluie tombée entre J-14 et J-7, J-21 et J-14, J-28 et J-21, J-42 et J-28 |
| Température | moyennes sur 3, 7, 14, 21, 30 jours ; variation sur une semaine (refroidissement) ; Tmax extrêmes (> 28 °C) ; gel |
| Humidité du sol | SWI SIM2, ERA5-Land 0–7 / 7–28 cm, ou bilan hydrique « seau » maison (pluie − évapotranspiration) |
| Air | humidité relative, déficit de pression de vapeur (VPD) |
| Saison | jour de l'année (sin/cos), degrés-jours depuis le 1er janvier (morilles) |
| Corrections locales | température corrigée de l'altitude (gradient ≈ -0,65 °C/100 m), exposition |

### Trouver les bonnes fenêtres temporelles

- **Fenêtres glissantes** : tester toutes les fenêtres (début, durée) et retenir la meilleure au sens de l'AICc — package R **`climwin`** ([Bailey & van de Pol 2016](https://doi.org/10.1371/journal.pone.0167980) ; [van de Pol et al. 2016](https://doi.org/10.1111/2041-210X.12590)).
- **Régression PLS sur séries journalières** : identifie les périodes où la température ou la pluie influencent la fructification, utilisée pour le matsutake au Yunnan ([Yang et al. 2012](https://doi.org/10.1007/s13225-012-0163-z)) ; package R `chillR`.
- **Modèles à retards distribués non linéaires (DLNM)** ([Gasparrini et al. 2010](https://doi.org/10.1002/sim.3940), package `dlnm`) : modélisent conjointement la forme de la réponse (optimum de température) et sa distribution dans le temps (retard de 1 à 6 semaines). Issus de l'épidémiologie, rarement utilisés en mycologie : **piste originale**.

### Apprendre la phénologie à partir de dates d'observation : la « niche phénologique »

Méthode de [Capinha (2019)](https://doi.org/10.1007/s00484-019-01714-0) et [Capinha et al. (2024)](https://doi.org/10.1093/biosci/biae041), la plus adaptée aux données disponibles :

1. **Positifs** : chaque observation datée (lieu, jour).
2. **Pseudo-absences temporelles** : **même lieu**, dates tirées au hasard dans la période d'étude (12 par observation dans l'étude de 2024).
3. **Variables** : météo des jours et semaines précédant chaque date (67 variables, réanalyse AgERA5).
4. **Classifieur** : forêt aléatoire + arbres boostés, et leur moyenne.
5. **Validation** : une année exclue à tour de rôle ; transfert à une autre région.

Résultats publiés : AUC 0,90 pour *Boletus edulis* et 0,88 pour *Macrolepiota procera* en Europe contre 0,83 pour un modèle de saisonnalité seule (2019) ; AUC moyenne 0,84 pour la chanterelle en tube, avec un bon transfert vers le Danemark (2024). Le principe : comparer les conditions *les jours d'observation* aux conditions *disponibles au même endroit*, ce qui neutralise en grande partie le biais spatial. **Notre étude de faisabilité reproduit cette méthode sur la France** ([chapitre 5](05-etude-de-faisabilite.md)).

### Autres familles

- **Modèles mixtes sur comptages journaliers** (données de placettes) : binomiale négative, température quadratique (optimum), pluie linéaire, effet aléatoire année ([Brejon Lamartinière & Hoffman 2025](https://www.biorxiv.org/content/10.64898/2025.12.12.693895v1.full)).
- **Modèles à deux étages (« hurdle »)** pour les rendements : P(présence) × rendement conditionnel, standard dans les travaux espagnols ([Taye et al. 2016](https://doi.org/10.1016/j.funeco.2016.05.008) ; [Morera et al. 2021](https://doi.org/10.1186/s40663-021-00297-w)).
- **Réseaux de neurones** sur fenêtres météo : précision de 60 à 80 % pour des amanites et russules en Hongrie, mais sur 28 jours de relevés seulement ([Somfalvi-Tóth et al. 2024](https://doi.org/10.1038/s41598-023-50638-8)). Les modèles de séquences (LSTM, TCN, Transformers) apprendraient les retards automatiquement, mais exigent beaucoup de données : à envisager en pré-entraînement multi-espèces sur l'Europe entière.
- **Modèles de processus** : bilan hydrique du sol (MEDFATE, utilisé par [Karavani et al. 2018](https://doi.org/10.1016/j.agrformet.2017.10.024) ; ISBA dans SIM2) → meilleures variables d'humidité que la pluie brute.

### Statistique ou machine learning ?

[Morera et al. 2021](https://doi.org/10.1186/s40663-021-00297-w) ont comparé 6 méthodes sur 98 placettes catalanes suivies de 1997 à 2019 : **les modèles à base d'arbres (RF, XGBoost) réduisent l'erreur de plus de 10 % par rapport aux autres méthodes d'apprentissage et de plus de 20 % par rapport aux modèles statistiques** (GLMM, régression géographiquement pondérée). Les réseaux de neurones donnent des cartes trop lisses, les SVM des valeurs négatives. Deux leçons supplémentaires :
- **La parcimonie aide l'extrapolation** : avec 5 variables climatiques au lieu de 15, la zone où le modèle extrapole hors de ses données diminue fortement.
- **Valider par blocs environnementaux** pour estimer l'erreur hors des conditions d'entraînement.

## 3.5 Combiner habitat et déclenchement

Deux architectures possibles :

1. **Produit de deux modèles** : `indice(x, t) = H(x) × F(x, t)` où H est le SDM (§ 3.3) et F le modèle de niche phénologique (§ 3.4). Simple, explicable (« bon habitat, mais trop sec »), chaque modèle est validé séparément. **Recommandé pour démarrer.**
2. **Modèle spatio-temporel unique** : un GBM entraîné sur des points de fond tirés dans l'espace *et* dans le temps (pondérés par l'effort), avec variables statiques et dynamiques. Capture des interactions (la pluie compte plus sur sol sableux) mais plus difficile à valider et à expliquer.

## 3.6 Vers de vraies probabilités : calibration et modèles intégrés

1. **Calibration** : dès que des absences existent (retours « rien trouvé » avec effort, placettes), ajuster une fonction monotone indice → probabilité (régression logistique de Platt, régression isotone), par espèce et par grande région.
2. **Modèles intégrés de distribution (ISDM)** ([Isaac et al. 2020](https://doi.org/10.1016/j.tree.2019.08.006) ; [Fletcher et al. 2019](https://doi.org/10.1002/ecy.2710) ; [Koshkina et al. 2017](https://doi.org/10.1111/2041-210X.12738)) : une seule vraisemblance combine les présences opportunistes (GBIF), les inventaires standardisés (placettes) et les sorties d'utilisateurs (détection/non-détection avec effort), avec un modèle de détection de type occupation ([MacKenzie et al. 2002](https://doi.org/10.1890/0012-9658(2002)083[2248:ESORWD]2.0.CO;2)). C'est l'objectif à moyen terme.
3. **Apprentissage actif** : proposer aux utilisateurs volontaires d'aller vérifier des zones où le modèle est incertain.

## 3.7 Pièges spécifiques aux champignons

| Piège | Effet | Parade |
|---|---|---|
| Effort d'observation lié à la météo (on sort après la pluie, le week-end, quand « ça pousse » dans les médias) | gonfle artificiellement l'effet de la pluie | témoin d'effort (espèce observée sans lien avec la météo, cf. hêtre au [chapitre 5](05-etude-de-faisabilite.md)) ; pondération par l'effort ; jour de semaine en covariable fixée à la prédiction |
| Persistance des sporophores (girolle : plusieurs semaines) | la date d'observation ≠ date d'émergence | modéliser la « présence de sporophores » et non l'émergence ; fenêtres plus longues |
| Détection imparfaite (trompettes discrètes) | sous-estimation | modèle de détection (§ 3.6) |
| Données taxonomiquement incertaines | bruit | groupes d'espèces ; filtrer sur la validation communautaire |
| Non-stationnarité climatique | modèle qui vieillit | réentraînement annuel ; cartes de similarité environnementale (ACP, MESS) pour signaler l'extrapolation |
| Autocorrélation spatiale et temporelle | validation trop optimiste | validation par blocs (§ 3.8) |

## 3.8 Validation

- **Découpages** : une année exclue (temporel), blocs spatiaux de 50–200 km, blocs environnementaux ([Roberts et al. 2017](https://doi.org/10.1111/ecog.02881) ; package `blockCV`, [Valavi et al. 2019](https://doi.org/10.1111/2041-210X.13107)).
- **Métriques présence seule** : AUC (relative), **indice de Boyce continu** ([Hirzel et al. 2006](https://doi.org/10.1016/j.ecolmodel.2006.05.017)), **enrichissement** (part des observations dans les 10 % de cellules les mieux notées), comparées à des **références** : saisonnalité seule, règle « pluie seule ».
- **Métriques avec absences** : score de Brier, courbes de fiabilité (calibration), précision/rappel.
- **Rejeu de saisons passées (hindcast)** : rejouer jour par jour les automnes 2018 (sec), 2022 (sécheresse), 2023 et 2024, et comparer l'indice national au nombre d'observations hebdomadaires (normalisé par l'effort).
- **Publier les résultats** : c'est un argument de différenciation face à la concurrence (aucun service existant ne publie de validation, [chapitre 4](04-existant-et-concurrence.md)).

## 3.9 Outils recommandés

- **Python** : `xarray`/`rioxarray`/`zarr` (grilles), `geopandas`/`shapely` (vecteurs), `h3` (hexagones), `scikit-learn`, **LightGBM**/XGBoost, `elapid` (MaxEnt), `mlflow` (suivi d'expériences).
- **R** (pour la recherche) : `biomod2`, `ENMeval`, `blockCV`, `climwin`, `dlnm`, `INLA`/`inlabru`, `Hmsc`.

[Chapitre suivant : l'existant et la concurrence →](04-existant-et-concurrence.md)
