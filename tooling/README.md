# Big Browser Hub — tooling (`bbhub`)

Transforme le **manifeste source unique** d'un Site (`site.yaml`) en artefacts Flatpak :
manifeste flatpak-builder, AppStream `metainfo.xml`, `.desktop`, `site.json` runtime, et copie
l'Engine partagé. Un seul fichier à éditer par les contributeurs.

## Installation

```sh
python3 -m pip install -r tooling/requirements.txt   # PyYAML
```

## Commandes

```sh
# Valider un manifeste (champs requis, id, url, icône…)
python3 tooling/bbhub.py validate sites/com.tekkengreg.bigbrowser.Wikipedia

# Générer les artefacts dans dist/<id>/
python3 tooling/bbhub.py generate sites/com.tekkengreg.bigbrowser.Wikipedia

# Générer puis builder via flatpak-builder (sur l'hôte)
python3 tooling/bbhub.py build sites/com.tekkengreg.bigbrowser.Wikipedia --install
flatpak run com.tekkengreg.bigbrowser.Wikipedia
```

### Icônes officielles cadrées (`icons.py`)

`tooling/icons.py` récupère le **logo officiel** d'un Site et l'enrobe dans le **cadre Big
Browser** (carte arrondie + contour violet `#6965db` + pastille « BB ») pour produire le
`icon.svg`. Le cadre signale visuellement qu'il s'agit d'un Site Big Browser, pas de l'app
officielle.

```sh
# Renseigner d'abord `icon_source: <URL du logo>` dans le site.yaml, puis :
python3 tooling/icons.py fetch sites/com.tekkengreg.bigbrowser.Spotify   # → icon.src.<ext>
python3 tooling/icons.py frame sites/com.tekkengreg.bigbrowser.Spotify   # → icon.svg
python3 tooling/icons.py build --all                                     # fetch + frame, tous les Sites
```

Sources SVG (imbriquées via `<svg>`) ou bitmap PNG/JPEG (data-URI). `frame --input logo.png`
accepte un fichier fourni à la main si vous n'avez pas d'URL. Les `icon.src.*` téléchargés sont
gitignorés : c'est le `icon.svg` commité (qui les embarque) qui est empaqueté.

## Entrée : `sites/<id>/`

Un Site se résume à **deux fichiers** :

```
sites/com.tekkengreg.bigbrowser.Wikipedia/
├── site.yaml     # manifeste source unique (cf. tooling/site.schema.json)
└── icon.svg      # icône (svg ou png ≥256²)
```

Le schéma complet des champs est dans [`site.schema.json`](site.schema.json) (utilisable aussi
pour l'autocomplétion/validation dans l'éditeur).

## Sortie : `dist/<id>/`

```
dist/com.tekkengreg.bigbrowser.Wikipedia/
├── com.tekkengreg.bigbrowser.Wikipedia.yml          # manifeste flatpak-builder
├── com.tekkengreg.bigbrowser.Wikipedia.metainfo.xml # AppStream
├── com.tekkengreg.bigbrowser.Wikipedia.desktop
├── site.json                            # config runtime (sous-ensemble)
├── icon.svg
└── bigbrowser.js                        # Engine copié (dédupliqué par OSTree au build)
```

## Dérivations notables

- **`finish-args`** déduits des permissions : `media` → `--device=all --socket=pulseaudio`,
  `notifications` → `--talk-name=org.freedesktop.Notifications`, plus `finish_args_extra`.
- **`site.json`** = sous-ensemble runtime du manifeste (id, url, allowed_domains, permissions, …).
- Validation : `appstreamcli validate` + `desktop-file-validate` (lancés en CI, Phase 4).
