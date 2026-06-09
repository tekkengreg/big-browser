# Big Browser

Un gros navigateur d'un nouveau genre : **chaque webapp devient une application autonome au
niveau système** — sa propre fenêtre, son icône, sa sandbox, son stockage. Là où un navigateur
classique empile des onglets, Big Browser promeut chaque site au rang d'application installable.

Chaque webapp est un **Site** : un *single-site browser* (GTK4 / WebKitGTK 6.0) empaqueté en
Flatpak et distribué via le **Big Browser Hub**, hébergé sur GitHub Pages.

> Feuille de route détaillée : [`ROADMAP.md`](ROADMAP.md).

## Structure

```
engine/     Moteur Big Browser (bigbrowser.js) — lit un site.json, affiche la WebView
sites/      1 dossier par Site : site.yaml + icon.svg (source unique)
tooling/    bbhub.py (génère les artefacts Flatpak) + catalog.py (catalogue + .flatpakref)
catalog/    (réservé)
.github/    Workflows CI (PR) et Publish (Pages)
```

## Utilisateur final

```sh
flatpak remote-add --if-not-exists bigbrowser https://<owner>.github.io/<repo>/bigbrowser.flatpakrepo
flatpak install bigbrowser io.bigbrowser.Wikipedia
```

## Contribuer un Site

1. Créer `sites/io.bigbrowser.MonSite/` avec `site.yaml` + `icon.svg`
   (voir [`tooling/site.schema.json`](tooling/site.schema.json) et l'exemple Wikipédia).
2. Valider et tester localement :
   ```sh
   python3 -m pip install -r tooling/requirements.txt
   python3 tooling/bbhub.py validate sites/io.bigbrowser.MonSite
   python3 tooling/bbhub.py build    sites/io.bigbrowser.MonSite --install
   flatpak run io.bigbrowser.MonSite
   ```
3. Ouvrir une Pull Request → la CI valide et builde automatiquement.
   Au merge sur `main`, le Site est publié sur le Hub.

## Mise en route du Hub (mainteneur)

### 1. GitHub Pages
Repo → **Settings → Pages → Source : GitHub Actions**.

### 2. Clé de signature GPG (recommandé)
Génère une clé dédiée et déclare-la en secrets pour signer le dépôt :

```sh
gpg --quick-generate-key "Big Browser Hub <hub@example.com>" default default never
gpg --list-secret-keys --keyid-format=long          # repère l'ID de la clé
gpg --armor --export-secret-keys <KEY_ID>           # → secret GPG_PRIVATE_KEY
```

Repo → **Settings → Secrets and variables → Actions** :
- `GPG_PRIVATE_KEY` : la clé privée exportée (bloc ASCII complet).
- `GPG_KEY_ID` : l'identifiant de la clé.

> Sans ces secrets, la publication fonctionne quand même mais le dépôt est **non signé**
> (un avertissement est émis). À éviter en production.

### 3. Premier déploiement
Pousser sur `main` (ou lancer le workflow **Publish** manuellement). Le dépôt OSTree signé et le
catalogue apparaissent sur l'URL Pages.

## Dépendances de dev

- Engine : `gjs`, `gtk4`, `webkitgtk6.0` (cf. [`engine/README.md`](engine/README.md)).
- Tooling : Python 3 + PyYAML.
- Build : `flatpak`, `flatpak-builder`.
