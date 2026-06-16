# Contribuer à Big Browser

Merci de votre intérêt ! La contribution la plus courante est **l'ajout d'un Site** : enrober une
webapp pour qu'elle devienne une application autonome distribuée par le Hub. Ce guide couvre ce
cas, puis les contributions au cœur (Engine / tooling).

## Ajouter un Site

Un Site se résume à **deux fichiers** : `site.yaml` (le manifeste) et `icon.svg` (l'icône). Tout
le reste — manifeste Flatpak, AppStream, `.desktop`, `site.json` runtime — est **généré** par le
tooling. Vous n'éditez jamais les artefacts à la main.

### 1. Créer le dossier du Site

Le dossier **doit** porter exactement l'`id` reverse-DNS sous le namespace `io.bigbrowser.*` :

```
sites/io.bigbrowser.MonSite/
├── site.yaml     # manifeste source unique
└── icon.svg      # icône (.svg, ou .png ≥ 256×256)
```

### 2. Rédiger `site.yaml`

Champs **requis** : `id`, `title`, `url`, `icon`, `summary`, `description`, `project_license`.
Le schéma complet (champs optionnels, validation, autocomplétion) est dans
[`tooling/site.schema.json`](tooling/site.schema.json). Exemple de référence :
[`sites/io.bigbrowser.Wikipedia/site.yaml`](sites/io.bigbrowser.Wikipedia/site.yaml).

```yaml
id: io.bigbrowser.MonSite          # = nom du dossier, doit commencer par io.bigbrowser.
title: Mon Site
url: https://app.example.com       # https:// obligatoire
icon: icon.svg
summary: Résumé en une ligne (≤ 200 caractères)
description: |
  Description longue (sert à la fiche AppStream du catalogue).
project_license: MIT               # licence de la webapp enrobée, ou LicenseRef-proprietary

# Comportement (optionnel)
allowed_domains: [app.example.com, cdn.example.com]   # l'hôte de url est ajouté d'office
permissions: { notifications: false, geolocation: false, media: false }
```

Quelques points qui font échouer la validation :
- l'`id` ne commence pas par `io.bigbrowser.` ou le dossier ne porte pas le même nom ;
- `url` n'est pas en `https://` ;
- l'icône référencée n'existe pas ou n'est pas `.svg`/`.png`.

> **Périmètre & marques** : on enrobe des sites tiers, on ne les usurpe pas. Le préfixe
> `io.bigbrowser.*` est obligatoire. Renseignez une `project_license` honnête (la licence de la
> webapp, pas la nôtre).

### 3. Valider et tester localement

```sh
python3 -m pip install -r tooling/requirements.txt          # PyYAML

python3 tooling/bbhub.py validate sites/io.bigbrowser.MonSite
python3 tooling/bbhub.py build    sites/io.bigbrowser.MonSite --install
flatpak run io.bigbrowser.MonSite
```

`build` nécessite `flatpak` + `flatpak-builder`. Pour juste inspecter les artefacts générés
(sans build) : `python3 tooling/bbhub.py generate sites/io.bigbrowser.MonSite` → `dist/<id>/`.

Si l'Engine refuse un site valide avec une erreur TLS (`UNKNOWN_CA`), voir le contournement
toolbox dans [`engine/README.md`](engine/README.md).

### 4. Ouvrir une Pull Request

À l'ouverture, la **CI** (`ci.yml`) valide, génère, lint (`desktop-file-validate`,
`appstreamcli validate`) et **builde** votre Site. Tout doit passer au vert.

Au **merge sur `main`**, le workflow `publish.yml` rebuilde le Hub et publie automatiquement votre
Site (dépôt OSTree signé + catalogue) sur GitHub Pages. Rien d'autre à faire.

## Contribuer au cœur (Engine / tooling)

- **Engine** ([`engine/bigbrowser.js`](engine/bigbrowser.js)) — GJS / GTK4 / WebKitGTK 6.0. Testez
  sans Flatpak : `gjs engine/bigbrowser.js examples/wikipedia.site.json`.
  ⚠️ L'Engine est **copié dans chaque Site au build** : toute modification impose que **tous les
  Sites soient rebâtis** (`publish.yml` le fait à chaque push sur `main`).
- **Tooling** ([`tooling/bbhub.py`](tooling/bbhub.py)) — la validation est faite à la main dans
  `validate()`. Un nouveau champ requis doit être ajouté **à la fois** dans `bbhub.py` et dans
  `tooling/site.schema.json`.

Voir [`CLAUDE.md`](CLAUDE.md) pour la vue d'ensemble de l'architecture (chaîne source → artefacts
→ Hub) et [`ROADMAP.md`](ROADMAP.md) pour les phases du projet.

## Style

Le code et la documentation sont **en français** — merci de conserver cette langue dans les
commentaires et messages. Restez cohérent avec le style des fichiers voisins.
