# 1. Écologie de la fructification : ce que dit la science

[← Retour au sommaire](README.md)

Ce chapitre résume ce que la littérature scientifique sait des facteurs qui font « sortir » un champignon. Il distingue trois niveaux de preuve : **consensus** (plusieurs études concordantes), **étude isolée** (un site, une espèce) et **règle empirique** (pratique de cueilleurs ou d'outils commerciaux, non validée).

## 1.1 Le champignon n'est que la partie visible

L'organisme vit en permanence dans le sol ou dans le bois sous forme de **mycélium**. Le sporophore (ce que l'on cueille) est une fructification éphémère, déclenchée par des conditions favorables. Ce que l'on veut prédire est donc la combinaison de deux choses très différentes :

1. **Le mycélium est-il là ?** C'est une question d'**habitat**, quasi statique à l'échelle d'une saison : arbre-hôte, sol, climat moyen, relief, histoire du peuplement.
2. **Va-t-il fructifier maintenant ?** C'est une question de **déclenchement**, dynamique à l'échelle du jour : humidité du sol, température, saison.

Deux grandes stratégies de nutrition, qui changent la façon de modéliser :

| Guilde | Exemples comestibles | Dépend de… | Conséquence pour le modèle |
|---|---|---|---|
| **Ectomycorhiziens** (symbiose avec les racines d'arbres) | cèpes, girolles, trompettes, pieds-de-mouton, lactaires, oronge, russules | la présence de l'**arbre-hôte** et du carbone qu'il fournit (photosynthèse) | la carte des essences forestières est la variable n° 1 de l'habitat ; la fructification suivrait l'activité photosynthétique de l'hôte, qui dépend de la température et chute en cas de sécheresse ([Sato et al. 2012](https://doi.org/10.1371/journal.pone.0049777)) |
| **Saprotrophes** (décomposeurs de litière, humus, bois) | coulemelle, rosé des prés, pied bleu, pleurote, mousserons | le **substrat** (litière, prairie, bois mort) et l'humidité locale | habitat plus diffus (prairies, lisières, bois mort) ; saisons souvent plus étalées ([Kauserud et al. 2012](https://doi.org/10.1073/pnas.1200789109)) |
| **Cas particulier : morilles** | *Morchella* spp. | sols calcaires ou remaniés, ripisylves, frênes/ormes/fruitiers, parfois brûlis | printanières, très dépendantes du réchauffement du sol |

## 1.2 Les déclencheurs météorologiques

### Humidité : la condition nécessaire

- **Consensus en climat méditerranéen** : la pluie de fin d'été et d'automne est le premier facteur de production. Sur 8 ans de placettes en pin sylvestre (Catalogne), la pluie de fin d'été/début d'automne est le facteur le plus fort ([Alday et al. 2017](https://doi.org/10.1038/srep45824)) ; même conclusion sur 17 ans en pin maritime (Espagne centrale, [Taye et al. 2016](https://doi.org/10.1016/j.funeco.2016.05.008)). Dans les modèles random forest de [Morera et al. 2022](https://doi.org/10.1016/j.agrformet.2022.108918), les variables de pluie (août–octobre) pèsent **≈ 70 %** de l'importance, contre ≈ 30 % pour les températures maximales.
- **L'humidité du sol vaut mieux que la pluie brute.** [Karavani et al. 2018](https://doi.org/10.1016/j.agrformet.2017.10.024) remplacent la pluie par l'humidité du sol simulée par un modèle de bilan hydrique (28 placettes, 2008–2015) ; le service météo tchèque (ČHMÚ) bâtit sa carte sur la **saturation du sol par les pluies des 30 derniers jours** ([Seznam Zprávy 2024](https://www.seznamzpravy.cz/clanek/domaci-rostou-meteorologove-zacali-zverejnovat-mapu-pravdepodobneho-rustu-hub-252787)).
- **La demande évaporative compte aussi** : une évapotranspiration plus forte réduit les rendements en climat méditerranéen ([Ágreda et al. 2015](https://doi.org/10.1111/gcb.12960)).

### Température : le métronome

- **Consensus en climat tempéré** : la température règle surtout *la date* de fructification. Sur 6,1 millions d'observations mondiales, la date et la durée de fructification sont liées à la moyenne et à la variabilité de la température, beaucoup moins aux pluies ([Krah et al. 2023](https://doi.org/10.1111/ele.14275)). À l'échelle européenne, la température pilote les espèces ectomycorhiziennes et saprotrophes d'automne ; la latitude décale la saison d'environ 25 jours et l'altitude jusqu'à 30 jours ([Andrew et al. 2018](https://doi.org/10.1002/ecy.2237)).
- **Optimum autour de 13 °C pour le cèpe** (étude isolée, préprint non relu par les pairs) : 10 ans de suivi quasi exhaustif d'une population de *Boletus edulis* en hêtraie près de Bielefeld (1 905 sporophores) montrent un pic de fructification pour une température moyenne d'environ **13 °C** et une hausse linéaire avec la pluie cumulée ; aucune fructification au-dessus d'environ 17,5 °C quand il pleut moins de 1 mm/j ([Brejon Lamartinière & Hoffman 2025](https://www.biorxiv.org/content/10.64898/2025.12.12.693895v1.full)). Notre étude de faisabilité trouve une température moyenne sur 14 jours de **13,1 °C** les jours d'observation du cèpe, contre 15,4 °C les jours témoins ([chapitre 5](05-etude-de-faisabilite.md)).
- **La chaleur inhibe** : des pics brutaux de température maximale freinent la production de cèpes dans les peuplements peu éclaircis ([Salerni et al. 2023](https://italianmycology.unibo.it/article/view/16464)) ; les températures maximales d'août à octobre sont négativement liées aux rendements ([Morera et al. 2021](https://doi.org/10.1186/s40663-021-00297-w)).
- **Choc thermique / refroidissement** : bien documenté pour le matsutake (fructification après quelques jours de sol sous ~19 °C) et intégré dans l'outil québécois de prévision du matsutake (choc thermique + réserve utile du sol ≥ 70 % + air entre 5 et 20 °C ; Biopterre 2013, rapport MAPAQ 12-C-139, voir [références](references.md)). Pour le cèpe, l'adage « orage chaud puis nuits fraîches » est cohérent avec ces mécanismes mais n'a pas de validation dédiée.
- **Morilles** : la meilleure variable de prédiction de la première sortie, dans un suivi au Missouri, est la température du sol accumulée sur les 20 jours précédents ; des travaux français (Buscot 1989) proposent des seuils en degrés-jours ([Mihail, NAMA](https://namyco.org/?p=1856)).

### Délais pluie → récolte

| Source | Délai annoncé | Statut |
|---|---|---|
| ČHMÚ (Tchéquie) | pousse la plus forte ~**10 jours** après une forte pluie suivie de temps chaud (pas trop) | règle opérationnelle |
| Champiscope (France) | premiers sporophores ~10 jours après 15–25 mm, pic à **2–3 semaines** | règle commerciale |
| Boletik (France) | récolte de cèpes **8–15 jours** après une vraie pluie | règle commerciale |
| Préprint Bielefeld | fenêtres de ~20 jours (température) et ~26 jours (pluie) | étude isolée |
| Notre étude (France, GBIF) | pluie tombée entre J-20 et J-14 : 17,6 mm les jours d'observation du cèpe contre 11,7 mm les jours témoins | données d'observation |

**À retenir :** il faut des variables météo *décalées* sur 1 à 6 semaines, pas seulement la météo du jour.

### Variabilité interannuelle et changement climatique

- Les rendements varient énormément d'une année à l'autre ([Boddy et al. 2014](https://doi.org/10.1016/j.funeco.2013.10.006)).
- En Suisse (115 417 comptages hebdomadaires, 1975–2006), la fructification s'est décalée de 12 jours plus tard après 1991 et l'abondance a augmenté ([Büntgen et al. 2013](https://boris.unibe.ch/49641)) ; en Europe, les saisons s'allongent et finissent plus tard ([Kauserud et al. 2012](https://doi.org/10.1073/pnas.1200789109)).
- **Conséquence :** un modèle entraîné sur 2000–2015 vieillit. Il faut le réentraîner chaque année et surveiller l'extrapolation.

## 1.3 Les facteurs de site (habitat)

- **Arbre-hôte** : décisif pour les mycorhiziens (voir fiches ci-dessous).
- **Sol** : pH (acide pour cèpe, girolle, chanterelle en tube ; calcaire pour morilles, lactaire délicieux, mousseron de la Saint-Georges), texture, réserve utile. L'acidité du sol augmente par exemple les rendements de *Lactarius* en pin maritime ([Taye et al. 2016](https://doi.org/10.1016/j.funeco.2016.05.008)).
- **Peuplement** : surface terrière, âge (l'âge et les sols sableux réduisent la production en pin maritime, [Taye et al. 2016](https://doi.org/10.1016/j.funeco.2016.05.008)), éclaircies (effet temporaire, [Salerni et al. 2023](https://italianmycology.unibo.it/article/view/16464)).
- **Relief** : altitude (décalage de saison), exposition (versants nord plus frais et humides), position topographique (fonds de vallons humides).
- **Perturbations** : incendies (morilles de feu), coupes rases (perte temporaire des mycorhiziens).

## 1.4 Fiches espèces (France)

Saisonnalité calculée sur les observations GBIF en France (part des observations par mois, en %, **hors dates par défaut au 1er du mois**). Les valeurs ≥ 20 % sont en gras. Script : [`research/feasibility/gbif_seasonality.py`](../../research/feasibility/gbif_seasonality.py).

| Espèce | Nom | Obs. | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| *Boletus edulis* | Cèpe de Bordeaux | 2 297 | <1 | <1 | <1 | <1 | <1 | 2 | 2 | 10 | **29** | **40** | 11 | 2 |
| *Boletus pinophilus* | Cèpe des pins | 226 | <1 | · | · | · | 2 | 12 | 5 | 14 | **31** | **27** | 6 | <1 |
| *Boletus aereus* | Cèpe bronzé / tête de nègre | 552 | <1 | <1 | <1 | <1 | 1 | 4 | 9 | 20 | **29** | **30** | 4 | <1 |
| *Boletus reticulatus* | Cèpe d'été / réticulé | 1 025 | <1 | <1 | <1 | <1 | 5 | **22** | 17 | 18 | 19 | 14 | 2 | 1 |
| *Imleria badia* | Bolet bai | 1 911 | <1 | <1 | <1 | <1 | <1 | 2 | 4 | 9 | **24** | **41** | 13 | 4 |
| *Cantharellus cibarius* | Girolle | 1 594 | <1 | <1 | <1 | <1 | 2 | 12 | 16 | 18 | **23** | 18 | 7 | 1 |
| *Craterellus cornucopioides* | Trompette de la mort | 913 | 2 | <1 | <1 | <1 | <1 | <1 | 5 | 8 | **21** | **41** | 18 | 4 |
| *Craterellus tubaeformis* | Chanterelle en tube | 1 324 | 3 | 2 | <1 | <1 | <1 | 1 | 2 | 6 | **21** | **38** | 20 | 8 |
| *Craterellus lutescens* | Chanterelle jaune | 256 | 4 | 1 | <1 | <1 | <1 | 2 | 2 | 9 | 19 | **26** | **24** | 12 |
| *Hydnum repandum* | Pied de mouton | 1 742 | 2 | <1 | <1 | <1 | <1 | 2 | 4 | 11 | **27** | **32** | 14 | 5 |
| *Morchella* | Morilles (genre) | 773 | <1 | <1 | 14 | **59** | **20** | 2 | <1 | <1 | <1 | <1 | <1 | <1 |
| *Lactarius deliciosus* | Lactaire délicieux | 583 | 1 | <1 | <1 | <1 | <1 | 1 | 2 | 3 | 10 | **40** | **35** | 6 |
| *Macrolepiota procera* | Coulemelle | 1 990 | <1 | <1 | <1 | <1 | 1 | 2 | 2 | 7 | **21** | **45** | 18 | 2 |
| *Calocybe gambosa* | Mousseron de la Saint-Georges | 399 | <1 | <1 | 4 | **38** | **41** | 10 | <1 | 1 | <1 | 1 | 2 | 2 |
| *Marasmius oreades* | Faux mousseron | 1 079 | <1 | <1 | <1 | 4 | 10 | 8 | 6 | 5 | 16 | **27** | 19 | 2 |
| *Lepista nuda* | Pied bleu | 1 158 | 3 | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 8 | **43** | **30** | 8 |
| *Pleurotus ostreatus* | Pleurote en huître | 823 | 10 | 4 | 3 | <1 | 1 | 2 | 2 | 6 | 11 | **25** | **21** | 14 |
| *Amanita caesarea* | Oronge | 360 | 1 | · | <1 | <1 | 1 | 3 | 2 | **24** | **33** | **29** | 5 | <1 |
| *Russula cyanoxantha* | Russule charbonnière | 2 719 | <1 | <1 | <1 | <1 | 2 | 10 | 14 | 15 | **28** | **24** | 4 | 1 |
| *Agaricus campestris* | Rosé des prés | 590 | 1 | 1 | <1 | <1 | 1 | 3 | 3 | 10 | **23** | **36** | 19 | <1 |
| *Sparassis crispa* | Sparassis crépu | 511 | 1 | <1 | · | · | <1 | 1 | 1 | 6 | **25** | **44** | 17 | 6 |
| *Tricholoma portentosum* | Petit-gris | 221 | 2 | · | · | <1 | <1 | <1 | 1 | 2 | 7 | **51** | **26** | 9 |
| *Hygrophorus marzuolus* | Hygrophore de mars | 193 | 3 | 14 | **34** | **24** | **21** | 1 | · | <1 | <1 | 1 | · | 1 |
| *Infundibulicybe geotropa* | Tête de moine | 615 | 1 | · | · | · | <1 | 1 | <1 | 2 | 8 | **35** | **37** | 14 |

Ces profils reflètent aussi l'**effort d'observation** (plus de sorties en automne et le week-end) : ils donnent la forme de la saison, pas une probabilité.

### Écologie des espèces prioritaires

Les associations ci-dessous sont les connaissances mycologiques classiques (guides de terrain et littérature citée) ; elles serviront de **contraintes a priori** (masques d'hôtes, signes attendus des effets) puis seront vérifiées par les données.

| Espèce | Hôtes / milieu | Sol | Déclencheurs connus | Confusions dangereuses |
|---|---|---|---|---|
| **Cèpe de Bordeaux** (*B. edulis*) | épicéa, sapin, hêtre, chênes, châtaignier, pins, bouleau | acide à neutre, drainé | pluie cumulée 2–4 semaines + T moyenne ~10–15 °C ; inhibé par la chaleur | bolet amer (non toxique, immangeable), bolets à pores rouges |
| **Cèpe des pins** (*B. pinophilus*) | pins (sylvestre), aussi épicéa/hêtre en montagne | acide | deux vagues : juin et automne | idem |
| **Cèpe bronzé** (*B. aereus*) | chênes, châtaigniers ; thermophile | acide à neutre | orages chauds de fin d'été | idem |
| **Cèpe d'été** (*B. reticulatus*) | chênes, hêtre, châtaignier | varié | dès mai–juin après orages chauds | idem |
| **Girolle** (*C. cibarius*) | hêtre, chênes, châtaignier, épicéa, pins | acide | longue saison ; sporophores qui persistent plusieurs semaines (moyenne citée : 44 jours, [Pilz et al. 2003](https://www.fs.usda.gov/pnw/pubs/gtr576.pdf)) | **clitocybe de l'olivier** (*Omphalotus olearius*) : confusion n° 1 en 2024 selon l'[ANSES](https://www.anses.fr/fr/content/cueillette-des-champignons-vigilance-face-aux-risques-dintoxications) ; fausse girolle |
| **Trompette de la mort** (*C. cornucopioides*) | feuillus (hêtre, chênes) | frais, limoneux à argileux | pluies d'automne, refroidissement | peu de confusions graves |
| **Pied de mouton** (*H. repandum*) | généraliste (feuillus et conifères) | tolère le calcaire | longue saison jusqu'en hiver | peu de confusions graves |
| **Morilles** (*Morchella* spp.) | frênes, ormes, peupliers, fruitiers, ripisylves, zones remaniées, brûlis | calcaire, limoneux | réchauffement printanier du sol (degrés-jours) ; pic en avril | **gyromitres** (toxiques) ; les morilles elles-mêmes sont toxiques crues ou mal cuites |
| **Lactaire délicieux / sanguin** | pins | calcaire | très dépendant des pluies de septembre–octobre (Catalogne) | autres lactaires |
| **Coulemelle** (*M. procera*) | lisières, clairières, prairies (saprotrophe) | varié | pluie cumulée 2–4 semaines | **petites lépiotes mortelles**, *Chlorophyllum* |
| **Mousseron de la Saint-Georges** (*C. gambosa*) | prairies, haies, lisières | calcaire | avril–mai | **inocybes** (dont l'inocybe de Patouillard), entolomes |
| **Oronge** (*A. caesarea*) | chênes, châtaigniers ; thermophile | acide à neutre | été chaud puis orages | **amanite tue-mouches** (chapeau délavé) ; œufs d'autres amanites, dont l'**amanite phalloïde** (mortelle) |

**Sécurité.** Pour la saison 1er juillet–31 décembre 2024, 1 363 personnes symptomatiques ont contacté un centre antipoison après consommation de champignons en France hexagonale, dont 3,1 % de cas graves et 3 décès ([ANSES](https://www.anses.fr/fr/content/cueillette-des-champignons-vigilance-face-aux-risques-dintoxications)). Une carte « girolles » doit donc systématiquement afficher le risque de confusion avec le clitocybe de l'olivier.

## 1.5 Ce que cela implique pour Mushroomator

1. **Deux couches de modèle** : habitat (où) × déclenchement (quand). Les mélanger dans une seule « note » opaque empêche de comprendre les erreurs.
2. **Modèles par espèce** (ou par groupe d'espèces proches) : les réponses diffèrent entre espèces bien plus qu'entre guildes ([Taye et al. 2016](https://doi.org/10.1016/j.funeco.2016.05.008) ; [Diez et al. 2013](https://deepblue.lib.umich.edu/bitstream/2027.42/100145/1/gcb12278.pdf)).
3. **Variables météo décalées** (1–8 semaines), humidité du sol plutôt que pluie brute, température moyenne sur 1–3 semaines, extrêmes (chaleur, gel).
4. **Effets régionaux** : la pluie limite au sud (méditerranéen), la température cadence au nord et en montagne ([Collado et al. 2019](https://repositori.udl.cat/items/748181eb-3e9e-40f9-a8dd-99e4fc6f8028) : lien production–climat plus fort en milieu méditerranéen).
5. **Réentraînement annuel** : la phénologie se décale avec le réchauffement.

[Chapitre suivant : sources de données →](02-sources-de-donnees.md)
