# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Vue d'ensemble

Big Browser promeut chaque webapp au rang d'**application autonome** : un *single-site browser*
GTK4 / WebKitGTK 6.0, empaqueté en Flatpak, avec sa propre fenêtre, son icône, sa sandbox et son
stockage isolé. Les Sites sont distribués via le **Big Browser Hub** (dépôt OSTree + catalogue)
hébergé sur GitHub Pages.

Le code et la documentation sont en français — conserver cette langue dans les nouveaux
commentaires et messages.

## Architecture : la chaîne source → artefacts → Hub

Le point central à comprendre est qu'**un contributeur n'édite que deux fichiers par Site**
(`site.yaml` + `icon.svg`), et que tout le reste est dérivé. Le flux complet :

```
sites/<id>/site.yaml   ──bbhub.py generate──▶   dist/<id>/   ──flatpak-builder──▶   repo/ (OSTree)
sites/<id>/icon.svg                              ├ <id>.yml          (manifeste flatpak-builder)
                                                 ├ <id>.metainfo.xml (AppStream)
                                                 ├ <id>.desktop
                                                 ├ site.json         (config runtime, sous-ensemble)
                                                 ├ icon.svg
                                                 └ bigbrowser.js      (Engine copié, dédupliqué par OSTree)
```

- **`engine/bigbrowser.js`** — Moteur générique unique (`gjs`). Lit un `site.json` et l'affiche
  dans une WebView. Le **même Engine est copié dans chaque Site** au moment de `generate` ; OSTree
  le dédoublonne entre tous les Sites au build. Toute évolution du comportement runtime se fait ici.
- **`tooling/bbhub.py`** — Dérive les artefacts Flatpak depuis `site.yaml`. C'est lui qui contient
  la logique de mapping permissions → `finish-args` (`media` → `--device=all --socket=pulseaudio`,
  `notifications` → `--talk-name=org.freedesktop.Notifications`) et qui produit le `site.json`
  runtime (sous-ensemble défini par `RUNTIME_KEYS`).
- **`tooling/catalog.py`** — Génère le site web de découverte (`index.html`), le
  `bigbrowser.flatpakrepo` et les `.flatpakref` par Site. N'est invoqué qu'en publication.
- **`tooling/site.schema.json`** — Schéma JSON de référence du `site.yaml` (autocomplétion +
  doc des champs). **La validation à l'exécution est faite à la main dans `bbhub.py:validate()`**,
  pas via jsonschema : tout nouveau champ requis doit être ajouté aux deux endroits.

### Deux résolutions de manifeste à ne pas confondre

- **Source** (`site.yaml`, PyYAML) : ce qu'édite le contributeur, champs riches (AppStream, etc.).
- **Runtime** (`site.json`, lu par l'Engine en JSON) : sous-ensemble produit par `runtime_site_json()`.
  L'Engine résout son chemin dans l'ordre : argument CLI → `$BIGBROWSER_SITE` →
  `/app/share/$FLATPAK_ID/site.json` (cas Flatpak) → `./site.json`.

### Contraintes invariantes (validées par `bbhub.py`)

- L'`id` doit être en reverse-DNS sous `io.bigbrowser.*` **et** le dossier `sites/<id>/` doit
  porter exactement ce nom.
- `url` doit être en `https://`. L'hôte de `url` est **toujours** ajouté aux `allowed_domains`.
- Périmètre de navigation : tout lien hors `allowed_domains` (et toute pop-up) s'ouvre dans le
  navigateur système via `Gtk.UriLauncher` ; le Site reste cantonné à ses domaines.
- Permissions refusées par défaut (notifications / geolocation / media).

## Commandes

### Développer / tester l'Engine localement (sans Flatpak)

```sh
gjs engine/bigbrowser.js examples/wikipedia.site.json          # via argument
BIGBROWSER_SITE=examples/excalidraw.site.json gjs engine/bigbrowser.js
```

Dépendances hôte : `gjs gtk4 webkitgtk6.0` (Fedora : `sudo dnf install gjs gtk4 webkitgtk6.0`).

Si **« Unacceptable TLS certificate » / `UNKNOWN_CA`** sur un site valide → `glib-networking`
manquant. Cas Fedora **toolbox** (trust store vide) — pointer GnuTLS sur le bundle hôte et
désactiver le sandbox WebKit :

```sh
WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 \
  SSL_CERT_FILE=/run/host/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem \
  gjs engine/bigbrowser.js examples/wikipedia.site.json
```

(L'Engine force déjà `GDK_BACKEND=x11` en conteneur/toolbox pour éviter l'erreur Wayland 71.)

### Tooling : valider, générer, builder un Site

```sh
python3 -m pip install -r tooling/requirements.txt           # PyYAML

python3 tooling/bbhub.py validate sites/io.bigbrowser.Wikipedia
python3 tooling/bbhub.py generate sites/io.bigbrowser.Wikipedia            # → dist/<id>/
python3 tooling/bbhub.py build    sites/io.bigbrowser.Wikipedia --install  # nécessite flatpak-builder
flatpak run io.bigbrowser.Wikipedia
```

> En conteneur/CI, `flatpak-builder` requiert `--disable-rofiles-fuse` (déjà passé par le tooling).

### Lint des artefacts (ce que fait la CI)

```sh
python3 tooling/bbhub.py generate sites/<id>
desktop-file-validate dist/<id>/<id>.desktop
appstreamcli validate --no-net dist/<id>/<id>.metainfo.xml
```

## CI/CD (GitHub Actions)

- **`ci.yml`** (sur PR touchant `sites/`, `engine/`, `tooling/`) : matrice sur chaque Site →
  validate + generate + lint + `flatpak-builder` **sans publication**. Garantit que tout compile.
- **`publish.yml`** (sur push `main`, mêmes paths) : rebuilde **tous** les Sites dans un dépôt
  OSTree (signé GPG si les secrets `GPG_PRIVATE_KEY` / `GPG_KEY_ID` existent, sinon non signé avec
  avertissement), génère le catalogue, et déploie sur GitHub Pages. Le dépôt est **régénéré
  intégralement** à chaque publication. Branche par défaut des refs : `stable`. Runtime :
  `org.gnome.Platform//49`.

## Notes

- `wikissb.js` (racine) est un **prototype hérité** mono-site (GTK3 / WebKit2 4.1) antérieur à
  l'Engine générique ; ne pas s'en inspirer pour le code actuel (GTK4 / WebKit 6.0).
- `dist/`, `repo/`, `.flatpak-builder/` et `__pycache__/` sont générés et gitignorés.
- `ROADMAP.md` détaille les phases du projet.
