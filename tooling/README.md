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

### Captures d'écran (`shot.js`)

`tooling/shot.js` charge une URL dans une WebView GTK4 / WebKitGTK 6.0 et enregistre un PNG
pour le bloc `<screenshots>` de l'AppStream — c'est lui qui remplit le carrousel de la fiche
GNOME Logiciels.

```sh
gjs tooling/shot.js https://fr.wikipedia.org \
    sites/com.tekkengreg.bigbrowser.Wikipedia/screenshots/1.png
# [largeur] [hauteur] [attente_ms] en arguments optionnels (défaut 1504×1056, 4 s)
```

Les PNG déposés dans `sites/<id>/screenshots/` sont trouvés tout seuls par `generate` (tri par
nom) ; le champ `screenshots` du `site.yaml` n'est utile que pour pointer des images hébergées
ailleurs.

Comme `icons.py`, c'est un **outil de dev** : il n'est pas lancé par la CI (qui n'a pas
d'affichage), et ce sont les PNG commités qui sont publiés. La fenêtre est brièvement visible
le temps de la capture — WebKit ne rend rien tant que la WebView n'est pas mappée.

> ⚠️ Toutes les webapps ne se laissent pas capturer : celles qui ouvrent un bandeau de
> consentement ou un mur de connexion (Spotify, par exemple) donnent une image inutilisable.
> Mieux vaut alors ne pas commiter de capture : GNOME Logiciels masque simplement le carrousel.

## Entrée : `sites/<id>/`

Un Site se résume à **deux fichiers** (plus, facultatif, un dossier de captures) :

```
sites/com.tekkengreg.bigbrowser.Wikipedia/
├── site.yaml       # manifeste source unique (cf. tooling/site.schema.json)
├── icon.svg        # icône (svg ou png ≥256²)
└── screenshots/    # facultatif : PNG pour la fiche du store (cf. shot.js)
    └── 1.png
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
- **Métadonnées du store** injectées d'office : liens du Hub et du dépôt GitHub (`urls` les
  surcharge), contrôles `keyboard`/`pointing`/`touch` d'après `form_factors`, et `<branding>`
  dérivé de `brand_color`.
- **Captures** : les PNG de `sites/<id>/screenshots/` deviennent des URLs
  `raw.githubusercontent.com` pointant sur `main`, **pas** sur le Hub — `appstreamcli compose`
  télécharge chaque image au build pour en relever les dimensions, or le Hub n'est déployé
  qu'*après* le build. Conséquence : dans une PR, l'image n'est pas encore sur `main`, le
  compose l'écarte en silence et le bundle de test n'a pas de capture ; elle apparaît à la
  première publication qui suit le merge.
- Validation : `appstreamcli validate` + `desktop-file-validate` (lancés en CI, Phase 4).
