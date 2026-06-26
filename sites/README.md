# Sites Big Browser

Un dossier par **Site** : `sites/<app-id>/`. Chaque Site est une webapp empaquetée en Flatpak
autonome, qui réutilise l'Engine partagé (`/engine/bigbrowser.js`).

## Anatomie d'un Site

Un Site se résume à **deux fichiers** (le reste est généré par le tooling) :

```
sites/com.tekkengreg.bigbrowser.Wikipedia/
├── site.yaml     # manifeste source unique (cf. tooling/site.schema.json)
└── icon.svg      # icône (svg ou png ≥256²)
```

Le manifeste flatpak-builder, le `metainfo.xml`, le `.desktop` et le `site.json` runtime sont
**dérivés automatiquement** par `tooling/bbhub.py` dans `dist/<id>/`.

## Comment ça s'assemble

- Le manifeste installe l'Engine dans `/app/bin/bigbrowser` (source unique `../../engine/`,
  dédupliquée par OSTree entre tous les Sites).
- Il installe `site.json` dans `/app/share/<app-id>/site.json`.
- `command: bigbrowser` lance l'Engine qui, via `$FLATPAK_ID`, trouve son `site.json` tout seul.
- Le stockage du Site (cookies, etc.) est isolé par Flatpak dans `~/.var/app/<app-id>/`.

## Builder & tester un Site

> `flatpak-builder` requis. En conteneur/CI, ajouter `--disable-rofiles-fuse` (déjà géré par le tooling).

```sh
python3 tooling/bbhub.py validate sites/com.tekkengreg.bigbrowser.Wikipedia
python3 tooling/bbhub.py build    sites/com.tekkengreg.bigbrowser.Wikipedia --install
flatpak run com.tekkengreg.bigbrowser.Wikipedia
```

## Vérifications qualité (avant publication)

```sh
python3 tooling/bbhub.py generate sites/<id>
desktop-file-validate dist/<id>/<id>.desktop
appstreamcli validate  dist/<id>/<id>.metainfo.xml
```
