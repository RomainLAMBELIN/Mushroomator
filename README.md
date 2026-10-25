# Mushroomator

Carte de chaleur indicative des champignons comestibles, espèce par espèce, calculée à partir de la météo passée et prévue, des arbres-hôtes, du sol et du relief. Usage personnel et gratuit.

**Zone couverte : Rhône-Alpes et alentours** (Massif central oriental → Alpes, Jura sud → Drôme provençale).
**Espèces :** cèpe de Bordeaux, girolle, trompette de la mort, chanterelle en tube, pied de mouton, morilles, hygrophore de mars, lactaire délicieux, oronge.

> **Outil indicatif, jamais d'identification.** La carte dit où et quand chercher, pas si un champignon est comestible. Faites toujours contrôler votre cueillette par un pharmacien ou un mycologue. En cas de symptômes après un repas de champignons, appelez le 15 ou un centre antipoison.

## Objectif

**Aider à identifier les coins à champignons** : dire où chercher, à l'échelle du coin (quelques dizaines de mètres), et quand y aller.

Aujourd'hui, l'outil est fiable pour le *quand* (météo des semaines précédentes), pas pour le *où* : pour le cèpe ou la girolle, la couche habitat ne fait guère mieux que « c'est une forêt ». Les essais avec les données publiques les plus fines (LiDAR HD, relief, cours d'eau, peuplement au point) n'ont pas permis de situer les coins ; la méthode retenue s'appuie sur vos propres sorties, notées dans un carnet privé dont l'outil apprend. Détails dans le [chapitre 8 du dossier](docs/recherche/08-identifier-les-coins.md).

## Sur le téléphone, sans rien installer

**Adresse : https://romainlambelin.github.io/Mushroomator/** (une fois la mise en ligne ci-dessous faite).

- La carte s'ouvre dans le navigateur du téléphone (Safari, Chrome, Firefox) : pas de magasin d'applications, pas d'ordinateur à laisser allumé. La météo est mise à jour **chaque nuit** par GitHub.
- Choisissez l'**espèce** et le **jour** (J-7 à J+7) ; la frise montre les conditions moyennes de chaque jour. **Indice** = habitat × conditions ; **Habitat** = arbres-hôtes, altitude, sol ; **Conditions** = météo comparée aux jours habituels de la saison.
- **Rechercher un lieu** avec la barre du haut : commune, lieu-dit, sommet, col, forêt, lac ou adresse (service de recherche de l'IGN), ou des coordonnées GPS (« 45.325, 5.764 », utilisables même hors ligne).
- **Touchez** la carte pour voir le détail du calcul et la météo du secteur ; le bouton ◎ centre la carte sur votre position.
- **Carnet de sorties** (📓) : notez chaque sortie en touchant la carte ou avec votre position, l'espèce, et « Trouvé » ou « Rien trouvé ». Les sorties restent sur le téléphone (rien n'est envoyé) ; exportez le carnet de temps en temps (*Exporter* / *Importer*).
- **Semblables** : à partir des coins où vous avez trouvé une espèce, la carte montre les peuplements qui leur ressemblent à moins de 25 km (même essence, altitude et sol proches), selon les conditions du jour. Avec 10 sorties notées le jour même, le carnet affiche votre taux de réussite selon l'indice : la mesure de fiabilité qui compte pour vous.
- **En forêt sans réseau** : la carte, les données de la dernière visite et les fonds de carte déjà affichés restent disponibles. Si la météo enregistrée date d'un jour précédent, la carte l'indique (« mise à jour du … »). Avec un réseau trop faible, elle s'affiche au bout de 4 secondes avec la dernière météo enregistrée.
- Volume : ~4,4 Mo à la première visite (forêts, relief, sols), puis ~60 Ko par jour.
- Facultatif : *Ajouter à l'écran d'accueil* (Safari : bouton Partager ; Chrome : menu ⋮) crée une icône qui ouvre la carte en plein écran. Ce n'est qu'un raccourci, rien n'est installé. Sur iPhone, Safari efface les données d'un site qu'on n'a pas ouvert depuis 7 jours, sauf s'il est sur l'écran d'accueil : ouvrez la carte avant de partir si vous ne l'avez pas consultée depuis une semaine.

### Mise en ligne sur GitHub Pages (une seule fois)

1. Rendre le dépôt public : *Settings → General → Danger Zone → Change repository visibility → Public* (GitHub Pages est gratuit pour un dépôt public).
2. *Settings → Pages → Build and deployment → Source* : **GitHub Actions**.
3. *Actions → Mise à jour de la carte → Run workflow* (~10 minutes). L'adresse s'affiche ensuite dans *Settings → Pages* et dans le résumé du workflow.

Ensuite, tout est automatique ([`.github/workflows/carte.yml`](.github/workflows/carte.yml)) : chaque nuit et à chaque modification de l'application, le workflow lance les tests, télécharge la météo puis publie la carte. La mise à jour de la nuit est lancée à 1 h 17 UTC (carte en ligne vers 2 h 30 en hiver, 3 h 30 en été). GitHub démarre parfois ces tâches avec plusieurs heures de retard, ou pas du tout : deux autres tentatives, à 3 h 47 et 6 h 17 UTC, publient la carte si aucune n'a encore réussi ce jour-là, et ne font rien sinon. En attendant, la carte calcule le jour même avec la prévision de la veille et l'indique (« mise à jour du … »). Si toutes les tentatives échouent, la carte de la veille reste en ligne et l'onglet *Actions* montre l'erreur. *Run workflow* lance à tout moment une mise à jour à la main, avec la dernière prévision. GitHub suspend les tâches planifiées d'un dépôt public resté 60 jours sans modification : un clic sur *Enable workflow* dans l'onglet *Actions* les relance.

## Sur un ordinateur (facultatif)

Prérequis : Python ≥ 3.11.

```bash
git clone https://github.com/RomainLAMBELIN/Mushroomator.git
cd Mushroomator
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python -m mushroomator update   # météo du jour (Open-Meteo, ~6 min) + génération du site
.venv/bin/python -m mushroomator serve    # puis ouvrir http://127.0.0.1:8000
```

`update` télécharge pour 352 points de la région les 92 derniers jours et 8 jours de prévision (≈ 2 500 à 2 800 appels, sous la limite gratuite d'Open-Meteo de 10 000 par jour) et prépare le dossier `site/`. Le résultat est mis en cache pour la journée ; `--force` le retélécharge. Avec `serve --host 0.0.0.0`, un téléphone du même réseau Wi-Fi peut ouvrir `http://<adresse-de-l'ordinateur>:8000`, mais sans le mode hors-ligne ni la localisation, qui exigent une adresse HTTPS.

### Rejouer une date passée

```bash
.venv/bin/pip install -r requirements-build.txt
.venv/bin/python -m mushroomator update --replay-eobs 2023-10-12   # météo observée E-OBS (jusqu'à juin 2024)
```

## Reconstruire les données (facultatif)

Les couches et les modèles sont déjà fournis dans `assets/`. Pour les refaire :

```bash
.venv/bin/pip install -r requirements-build.txt
.venv/bin/python -m mushroomator layers     # forêts IGN (21 départements, ~700 Mo), relief, sols : ~15 min
.venv/bin/python -m mushroomator train      # E-OBS (~1,1 Go) + GBIF France/Suisse : ~20 min
.venv/bin/python -m mushroomator validate   # validation de l'habitat et rejeu des saisons 2011-2024
.venv/bin/python -m pytest
```

Les tables d'hôtes, de pH et d'altitude de chaque espèce sont dans [`mushroomator/species.toml`](mushroomator/species.toml) et peuvent être ajustées selon votre expérience (relancer ensuite `validate` puis `site`).

## Comment ça marche, et quelle fiabilité ?

- [Dossier de recherche](docs/recherche/README.md) : écologie de la fructification, données, méthodes, concurrence.
- [Prototype Rhône-Alpes](docs/recherche/07-prototype-rhone-alpes.md) : architecture, modèles et **résultats de validation**. En bref, à lieu fixe, l'indice est plus élevé le jour d'une observation réelle qu'un jour quelconque dans 79 à 91 % des cas selon l'espèce (rejeu 2011-2024). La couche habitat situe bien l'oronge, moyennement la trompette, la chanterelle en tube et le lactaire, mais pour le cèpe, la girolle et le pied de mouton elle ne fait guère mieux que « en forêt ».

## Structure

```
mushroomator/            paquet Python : sources de données, modèles, mise à jour, site
web/                     application web (Leaflet, calcul de la carte dans le navigateur)
assets/                  couches régionales, modèles et validation (versionnés)
docs/recherche/          dossier de recherche
research/feasibility/    étude de faisabilité initiale (reproductible)
tests/                   tests (dont la cohérence des calculs Python / JavaScript)
```

## Données et licences

Forêts : IGN BD Forêt® V2 (Licence Ouverte) · Relief : Copernicus DEM GLO-90 · Sols : ISRIC SoilGrids 2.0 (CC-BY 4.0) · Météo du jour : Open-Meteo.com (CC-BY 4.0, gratuit pour un usage non commercial) · Entraînement : observations GBIF.org (licences CC0, CC-BY, CC-BY-NC selon les jeux) et E-OBS (Copernicus / ECA&D, recherche et usage non commerciaux) · Fonds de carte : IGN, OpenTopoMap, OpenStreetMap · Recherche de lieux : géocodage IGN Géoplateforme · Carte : Leaflet (BSD-2).
