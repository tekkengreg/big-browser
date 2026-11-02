# Big Browser

Un gros navigateur d'un nouveau genre : **chaque webapp devient une application autonome au
niveau système** — sa propre fenêtre, son icône, sa sandbox, son stockage. Là où un navigateur
classique empile des onglets, Big Browser promeut chaque site au rang d'application installable.

Chaque webapp est un **Site** : un *single-site browser* (GTK4 / WebKitGTK 6.0) empaqueté en
Flatpak et distribué via le **Big Browser Hub**, hébergé sur GitHub Pages.

> Feuille de route détaillée : [`ROADMAP.md`](ROADMAP.md).

## Dans la fenêtre

Pas de barre d'adresse : un Site n'est pas un navigateur. Juste une barre d'en-tête avec un
bouton **Précédent** et un **menu** à deux réglages, **Langue** et **Thème**. Les deux suivent
le système par défaut et se surchargent par Site — un Site n'est donc jamais dédié à une
langue : Wikipédia s'ouvre dans l'édition du bureau, comme le ferait le site dans un
navigateur. Détails : [`engine/README.md`](engine/README.md).

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
flatpak install bigbrowser com.tekkengreg.bigbrowser.Wikipedia
```

### Dans GNOME Logiciels

Une fois le dépôt ajouté avec le `.flatpakrepo`, les Sites apparaissent dans
**GNOME Logiciels** comme n'importe quelle application : recherche, catégories,
fiche détaillée, mises à jour. Rien de spécifique n'est nécessaire — le dépôt
OSTree publie un catalogue AppStream (ref `appstream2/<arch>`, produit par
`flatpak build-update-repo`) avec les icônes rastérisées en 48/64/128 px.

Ce qui alimente la fiche :

| Élément de la fiche | Source |
|---|---|
| Nom, résumé, description, catégories, mots-clés | `site.yaml` → `metainfo.xml` |
| Icône | `icon.svg` (cadré BB) |
| Carrousel de captures | PNG de `sites/<id>/screenshots/` (cf. `tooling/shot.js`) |
| Teinte de la tuile de mise en avant | `brand_color` → `<branding>` |
| Classement d'âge | `content_rating` (vide par défaut, comme les navigateurs empaquetés) |
| « Nouveautés » | `release_notes` |
| Éditeur | `developer_name` |
| Liens (site web, aide, bug, code source, contribuer) | `urls` + liens du Hub injectés par `bbhub.py` |
| Permissions affichées (« Réseau », « Périphériques »…) | `finish-args` dérivés de `permissions` |
| Vignette « Matériel » (« Adaptatif » / « Ordinateur uniquement ») | `form_factors` → `<recommends><control>` |
| Dépôt d'origine (titre, logo, description) | `bigbrowser.flatpakrepo` |

Un Site n'étant qu'une WebView sans taille minimale, il est déclaré
**adaptatif** par défaut : clavier + pointeur + tactile en `recommends` — qui
veut dire « supporte » au sens AppStream, un `requires` déclencherait au
contraire une vignette rouge. GNOME Logiciels affiche alors la vignette verte
« Adaptatif — Fonctionne sur téléphones, tablettes et ordinateurs » ; sans ces
relations, il retombe sur son repli « Ordinateur uniquement ». Pour un Site dont
la webapp n'est pas responsive :

```yaml
form_factors: [desktop]
```

> ⚠️ **Préférer le `.flatpakrepo` au `.flatpakref`.** Un `.flatpakref` (bouton
> « Installer » du catalogue) réutilise le dépôt `bigbrowser` s'il est déjà
> configuré ; sinon, grâce à `SuggestRemoteName`, flatpak propose de l'ajouter
> sous ce nom — mais sans titre, logo ni description, car flatpak ne lit ces
> champs que dans le groupe `[Flatpak Repo]` d'un `.flatpakrepo`. Si
> l'utilisateur refuse, flatpak retombe sur un dépôt `<id>-origin` marqué
> `xa.noenumerate=true` : le Site s'installe et se met à jour, mais **le reste du
> catalogue reste invisible** dans GNOME Logiciels.

## Contribuer un Site

1. Créer `sites/com.tekkengreg.bigbrowser.MonSite/` avec `site.yaml` + `icon.svg`
   (voir [`tooling/site.schema.json`](tooling/site.schema.json) et l'exemple Wikipédia).
2. Valider et tester localement :
   ```sh
   python3 -m pip install -r tooling/requirements.txt
   python3 tooling/bbhub.py validate sites/com.tekkengreg.bigbrowser.MonSite
   python3 tooling/bbhub.py build    sites/com.tekkengreg.bigbrowser.MonSite --install
   flatpak run com.tekkengreg.bigbrowser.MonSite
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

- Engine : `gjs`, `gtk4`, `libadwaita`, `webkitgtk6.0` (cf. [`engine/README.md`](engine/README.md)).
- Tooling : Python 3 + PyYAML.
- Build : `flatpak`, `flatpak-builder`.
