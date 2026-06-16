# Big Browser — Engine

Moteur générique : lit un manifeste de **Site** (`site.json`) et l'affiche dans une WebView
**GTK4 / WebKitGTK 6.0**, isolée et indépendante au niveau système.

## Dépendances (test local)

Le moteur tourne sous `gjs` avec les *typelibs* GTK 4 et WebKitGTK 6.0.

- **Fedora** : `sudo dnf install gjs gtk4 webkitgtk6.0`
- **Debian/Ubuntu** : `sudo apt install gjs gir1.2-gtk-4.0 gir1.2-webkit-6.0`
- **Arch** : `sudo pacman -S gjs gtk4 webkitgtk-6.0`

> En production, ces dépendances sont fournies par le runtime Flatpak `org.gnome.Platform` :
> rien à installer côté utilisateur final.

## Lancer un Site

Le manifeste est résolu dans l'ordre : argument CLI → `$BIGBROWSER_SITE` →
`/app/share/<app-id>/site.json` (cas Flatpak) → `./site.json`.

```sh
# Via argument
gjs engine/bigbrowser.js examples/wikipedia.site.json

# Via variable d'environnement
BIGBROWSER_SITE=examples/excalidraw.site.json gjs engine/bigbrowser.js
```

## Format du manifeste

| Champ | Requis | Rôle |
|-------|:------:|------|
| `url` | ✅ | URL de la webapp à charger |
| `id` | — | app-id (défaut : `io.bigbrowser.UnnamedSite`) ; isole cookies/stockage |
| `title` | — | titre de fenêtre (défaut : `id`) |
| `icon` | — | nom de fichier icône (utilisé à l'empaquetage, pas au runtime) |
| `allowed_domains` | — | domaines internes ; l'hôte de `url` est toujours ajouté. Hors liste → navigateur système |
| `permissions.notifications` | — | autorise les notifications (défaut : refus) |
| `permissions.geolocation` | — | autorise la géolocalisation (défaut : refus) |
| `permissions.media` | — | autorise caméra/micro (défaut : refus) |
| `inject_css` | — | feuille de style injectée dans toutes les frames |
| `inject_js` | — | script injecté en fin de chargement (frame principale) |
| `ignore_tls_errors` | — | **debug uniquement** : désactive la validation TLS (défaut : refus) |

## Dépannage

**« Unacceptable TLS certificate » sur un site valide** → il manque le backend TLS de GIO.
Installez `glib-networking` (et `ca-certificates`) :

- Fedora : `sudo dnf install glib-networking ca-certificates`
- Debian/Ubuntu : `sudo apt install glib-networking ca-certificates`

Sans `glib-networking`, WebKitGTK n'a aucune base de certificats et rejette **tout** HTTPS.
L'Engine logge la cause exacte (`UNKNOWN_CA`, `EXPIRED`, …) au démarrage en cas d'échec TLS.

**Cas Fedora toolbox** : l'image toolbox a souvent un trust store vide
(`/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem` à 0 octet) → `UNKNOWN_CA` sur tout site,
y compris quand l'hôte fonctionne. Pour du dev depuis la toolbox, pointez GnuTLS sur le bundle
de l'hôte (monté sous `/run/host`) et désactivez le sandbox WebKit (qui sinon ne voit pas ce
chemin) :

```sh
WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 \
  SSL_CERT_FILE=/run/host/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem \
  gjs engine/bigbrowser.js examples/wikipedia.site.json
```

Cela ne concerne **que** l'environnement de dev : en Flatpak, l'utilisateur final a un trust
store complet et un GPU natif, aucune de ces variables n'est nécessaire.

## Comportements

- **Isolation** : chaque Site a sa propre `NetworkSession` (cookies SQLite persistants) sous
  `~/.local/share/bigbrowser/<id>/`.
- **Périmètre** : les liens hors `allowed_domains` (et toute tentative de pop-up) s'ouvrent dans
  le navigateur système via `Gtk.UriLauncher`.
- **Titre dynamique** : `<titre de page> — <titre du Site>`.
- **Raccourcis** : `Ctrl +/-/0` (zoom), `F5` ou `Ctrl+R` (recharger).
- **Géométrie** : taille de fenêtre persistée sous `~/.local/share/bigbrowser/<id>/window-state.json`.
- **Téléchargements** : enregistrés sans dialogue dans le dossier Téléchargements XDG
  (`~/Téléchargements`, repli `$HOME`) ; collisions de noms gérées (`fichier (1).ext`). En Flatpak,
  l'accès en écriture est fourni par le `finish-arg` `--filesystem=xdg-download:create` (ajouté
  d'office par le tooling).
- **Menu contextuel** : épuré pour une app mono-site — édition (copier/coller…), liens et
  téléchargements conservés ; ouverture en nouvelle fenêtre et inspecteur retirés.
