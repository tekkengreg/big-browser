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
python3 tooling/bbhub.py validate sites/io.bigbrowser.Wikipedia

# Générer les artefacts dans dist/<id>/
python3 tooling/bbhub.py generate sites/io.bigbrowser.Wikipedia

# Générer puis builder via flatpak-builder (sur l'hôte)
python3 tooling/bbhub.py build sites/io.bigbrowser.Wikipedia --install
flatpak run io.bigbrowser.Wikipedia
```

## Entrée : `sites/<id>/`

Un Site se résume à **deux fichiers** :

```
sites/io.bigbrowser.Wikipedia/
├── site.yaml     # manifeste source unique (cf. tooling/site.schema.json)
└── icon.svg      # icône (svg ou png ≥256²)
```

Le schéma complet des champs est dans [`site.schema.json`](site.schema.json) (utilisable aussi
pour l'autocomplétion/validation dans l'éditeur).

## Sortie : `dist/<id>/`

```
dist/io.bigbrowser.Wikipedia/
├── io.bigbrowser.Wikipedia.yml          # manifeste flatpak-builder
├── io.bigbrowser.Wikipedia.metainfo.xml # AppStream
├── io.bigbrowser.Wikipedia.desktop
├── site.json                            # config runtime (sous-ensemble)
├── icon.svg
└── bigbrowser.js                        # Engine copié (dédupliqué par OSTree au build)
```

## Dérivations notables

- **`finish-args`** déduits des permissions : `media` → `--device=all --socket=pulseaudio`,
  `notifications` → `--talk-name=org.freedesktop.Notifications`, plus `finish_args_extra`.
- **`site.json`** = sous-ensemble runtime du manifeste (id, url, allowed_domains, permissions, …).
- Validation : `appstreamcli validate` + `desktop-file-validate` (lancés en CI, Phase 4).
