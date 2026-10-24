# Mushroomator

Carte de chaleur indicative des champignons comestibles, espèce par espèce, calculée à partir de la météo passée et prévue, des arbres-hôtes, du sol et du relief. Usage personnel et gratuit.

**Zone couverte : Rhône-Alpes et alentours** (Massif central oriental → Alpes, Jura sud → Drôme provençale).
**Espèces :** cèpe de Bordeaux, girolle, trompette de la mort, chanterelle en tube, pied de mouton, morilles, hygrophore de mars, lactaire délicieux, oronge.

> **Outil indicatif, jamais d'identification.** La carte dit où et quand chercher, pas si un champignon est comestible. Faites toujours contrôler votre cueillette par un pharmacien ou un mycologue. En cas de symptômes après un repas de champignons, appelez le 15 ou un centre antipoison.

## Utilisation quotidienne

Prérequis : Python ≥ 3.11.

```bash
git clone https://github.com/RomainLAMBELIN/Mushroomator.git
cd Mushroomator
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python -m mushroomator update   # météo du jour (Open-Meteo, ~6 min) + génération du site
.venv/bin/python -m mushroomator serve    # puis ouvrir http://127.0.0.1:8000
```

`update` télécharge pour 352 points de la région les 92 derniers jours et 8 jours de prévision (≈ 2 500 à 2 800 appels, sous la limite gratuite d'Open-Meteo de 10 000 par jour) et prépare le dossier `site/`. Le résultat est mis en cache pour la journée ; `--force` le retélécharge.

Sur la carte :
- choisissez l'**espèce** et le **jour** (J-7 à J+7) ; la frise montre les conditions moyennes de chaque jour ;
- **Indice** = habitat × conditions ; **Habitat** = arbres-hôtes, altitude, sol ; **Conditions** = météo comparée aux jours habituels de la saison ;
- **cliquez** n'importe où pour voir le détail du calcul et la météo du secteur ;
- le bouton ◎ centre la carte sur votre position.

### Sur le téléphone

- **Même réseau Wi-Fi** : `python -m mushroomator serve --host 0.0.0.0`, puis ouvrez `http://<adresse-de-l'ordinateur>:8000` sur le téléphone.
- **Depuis n'importe où, mise à jour automatique** : le workflow [`.github/workflows/carte.yml`](.github/workflows/carte.yml) met la carte à jour chaque matin et la publie sur GitHub Pages. Pour l'activer : *Settings → Pages → Source : GitHub Actions*, puis créez la variable de dépôt `MUSHROOMATOR_PAGES` = `true` (*Settings → Secrets and variables → Actions → Variables*). GitHub Pages est gratuit pour un dépôt public ; pour un dépôt privé, il faut une offre payante, ou alors un hébergeur statique gratuit (Netlify, Cloudflare Pages) qui publie le dossier `site/`.
- Une fois la page ouverte en HTTPS, « Ajouter à l'écran d'accueil » l'installe comme une application. Elle reste consultable sans réseau en forêt, avec les données et les fonds de carte déjà vus.

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

Forêts : IGN BD Forêt® V2 (Licence Ouverte) · Relief : Copernicus DEM GLO-90 · Sols : ISRIC SoilGrids 2.0 (CC-BY 4.0) · Météo du jour : Open-Meteo.com (CC-BY 4.0, gratuit pour un usage non commercial) · Entraînement : observations GBIF.org (licences CC0, CC-BY, CC-BY-NC selon les jeux) et E-OBS (Copernicus / ECA&D, recherche et usage non commerciaux) · Fonds de carte : IGN, OpenTopoMap, OpenStreetMap · Carte : Leaflet (BSD-2).
