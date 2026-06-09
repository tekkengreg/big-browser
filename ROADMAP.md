# Big Browser — Feuille de route

> **Big Browser** : un gros navigateur d'un nouveau genre, où **chaque webapp devient une
> application indépendante au niveau système** — sa propre fenêtre, sa propre icône, sa propre
> sandbox, son propre stockage. Là où un navigateur classique empile des onglets dans un seul
> processus, Big Browser promeut chaque site au rang d'application autonome.
>
> Chaque webapp encapsulée est un **Site** : un *single-site browser* en WebView, empaqueté en
> Flatpak et distribué via le **Big Browser Hub**, hébergé et automatisé sur GitHub.

---

## 1. Vision & principes

- **Un Site = une URL** affichée dans une WebView isolée (cookies/stockage dédiés), autonome
  vis-à-vis du système (fenêtre, icône, entrée menu, sandbox propres).
- **Repenser le navigateur** : pas d'onglets partagés ni de processus monolithique — chaque
  webapp vit comme une vraie application, installable et désinstallable indépendamment.
- **Soumission low-friction** : un contributeur fournit un manifeste de Site (URL, icône, titre
  + métadonnées), ouvre une *Pull Request*, et la CI s'occupe du build + publication.
- **Distribution standard** : dépôt Flatpak (OSTree) que n'importe qui ajoute avec
  `flatpak remote-add`, plus un catalogue web pour découvrir/installer.
- **100 % GitHub** : code, soumissions, CI/CD (Actions), hébergement (Pages), gouvernance (PR/Issues).

### Glossaire
| Terme | Sens |
|-------|------|
| **Big Browser** | Le projet / la plateforme dans son ensemble |
| **Site** | Unité de base : une webapp encapsulée, indépendante au niveau système |
| **Engine** | Le moteur partagé (GJS/GTK4 + WebKitGTK 6.0) qui lit un manifeste et affiche un Site ; packagé en BaseApp `io.bigbrowser.Engine` |
| **Manifeste de Site** | `site.yml` décrivant un Site (URL, icône, titre, métadonnées AppStream) |
| **Big Browser Hub** | Dépôt Flatpak (OSTree) + catalogue web de découverte |

### Conventions de nommage
- Namespace projet : **`io.bigbrowser.*`** (à fixer selon le domaine/org GitHub possédé ;
  repli possible : `io.github.<org>.*`).
- Moteur (BaseApp) : **`io.bigbrowser.Engine`**.
- Sites : **`io.bigbrowser.<NomDuSite>`** (ex. `io.bigbrowser.Wikipedia`). On enrobe des sites
  tiers : préfixer sous le namespace Big Browser évite d'usurper l'identité de marque du vendeur.

---

## 2. Architecture cible

```
┌──────────────────────────────────────────────────────────────┐
│  Monorepo GitHub — Big Browser                                 │
│                                                                │
│  /engine           → Moteur Big Browser (GJS/GTK4 + WebKit 6.0)│
│  /sites            → 1 dossier par Site soumis (manifestes)    │
│  /tooling          → CLI de validation + génération Flatpak    │
│  /catalog          → site statique de découverte (Pages)       │
│  /.github/workflows→ CI : lint, build, publication             │
│                                                                │
└──────────────────────────────────────────────────────────────┘
            │ build Flatpak (Actions)
            ▼
┌──────────────────────────────────────────────────────────────┐
│  Big Browser Hub = "Flathub sur GitHub"                        │
│   • Dépôt OSTree (dossier de fichiers statiques: objects/,     │
│     refs/, summary) généré par `flatpak build-export`          │
│   • Poussé par la CI sur la branche `gh-pages` → servi par     │
│     GitHub Pages en HTTPS (aucun serveur à gérer)              │
│   • .flatpakrepo (remote) + .flatpakref (install 1 clic)       │
└──────────────────────────────────────────────────────────────┘
```

### Comment fonctionne l'hébergement (le « Flathub sur GitHub »)

Un dépôt Flatpak **n'est pas un service** : c'est un **dossier de fichiers statiques** servi en
HTTPS. Le mécanisme, identique à Flathub :

1. La CI compile le Site et l'exporte dans un dépôt OSTree : `flatpak build-export repo/ <build>`.
   → produit un dossier `repo/` (`objects/`, `refs/`, `summary`, `summary.sig`...).
2. La CI pousse ce dossier `repo/` sur la branche **`gh-pages`** → **GitHub Pages** le sert
   automatiquement à une URL HTTPS publique.
3. L'utilisateur final n'a que deux commandes :
   ```sh
   flatpak remote-add --if-not-exists bigbrowser https://<user>.github.io/<repo>/bigbrowser.flatpakrepo
   flatpak install bigbrowser io.bigbrowser.Wikipedia
   flatpak update            # les MAJ marchent comme sur Flathub
   ```

C'est **exactement** le modèle Flathub, en remplaçant leur infra par GitHub Pages.

**Choix techniques retenus :**
- Engine : **GJS + GTK4 + WebKitGTK 6.0** (= `WebKit` 6.0 / `imports.gi.versions.WebKit = '6.0'`).
  Migration depuis le GTK3/WebKit2 4.1 actuel de `wikissb.js`. Pas de branche de compat GTK3.
- Empaquetage : **Flatpak** sur le runtime **`org.gnome.Platform//49`** (version stable supportée ;
  48 est EOL depuis mars 2026), qui fournit GTK4 + WebKitGTK 6.0.
- Format manifeste de Site : **YAML** (lisible, diff-friendly en PR) → converti en
  `flatpak-builder` JSON/YAML + AppStream `metainfo.xml` + `.desktop` par le tooling.

> **Note migration GTK4/WebKit6** : l'API diffère de `wikissb.js`. Principaux changements :
> `Gtk.init()` sans argument, plus de `Gtk.main()` (utiliser `Gtk.Application` + `GLib.MainLoop`
> ou `app.run()`), `win.set_child(webView)` au lieu de `win.add()`, `WebKit.WebView` /
> `WebKit.NetworkSession` (remplace `WebContext`/`WebsiteDataManager`), et l'ouverture de liens
> externes via `Gtk.UriLauncher` (remplace `Gtk.show_uri`).

### Mutualisation de l'Engine — pourquoi le dépôt reste petit

L'Engine est la seule brique « lourde » *relativement* aux Sites, qui ne sont que des
métadonnées. Trois mécanismes Flatpak/OSTree gardent le dépôt léger :

1. **WebKit n'est jamais dans le dépôt.** Le moteur web est fourni par `org.gnome.Platform`,
   téléchargé **une seule fois** côté utilisateur et partagé par tous les Sites.
2. **Le code de l'Engine est minuscule** (quelques Ko de GJS — `wikissb.js` fait 2 Ko).
3. **OSTree déduplique par contenu** : les fichiers identiques entre Sites ne sont stockés
   qu'une fois. N Sites ≈ 1× Engine + N× quelques Ko de métadonnées (icône, `.desktop`,
   `metainfo.xml`, `site.json`).

**Décision d'architecture : l'Engine est livré comme module Flatpak partagé.**
- Source unique : `/engine/bigbrowser.js`. Chaque manifeste de Site inclut un module `engine`
  qui installe ce script dans `/app/bin/bigbrowser`. OSTree déduplique le binaire identique
  entre tous les Sites → coût stockage ≈ 1× l'Engine.
- `command: bigbrowser` lance l'Engine, qui retrouve son `site.json` via `$FLATPAK_ID`
  (`/app/share/<app-id>/site.json`). Le Site n'ajoute que ses métadonnées.
- *(Le BaseApp Flatpak `base:` a été écarté : pertinent pour une toolchain lourde — Qt, Electron —
  mais surdimensionné pour un script de quelques Ko, et il impose un build+publish préalable.)*
- ⚠️ Mettre à jour l'Engine impose de **rebuilder tous les Sites** (le script est copié au build).
  À automatiser via un rebuild matriciel en CI (déclenché quand `/engine` change).

---

## 3. Composants & livrables

### 3.1 Engine — moteur Big Browser (`/engine`)
Généraliser `wikissb.js` pour qu'il ne soit plus codé en dur sur Wikipedia.

- [ ] Lire la config au démarrage (variable d'env `BIGBROWSER_SITE` ou fichier installé
      `/app/share/<app-id>/site.json`) : `url`, `title`, `allowed_domains[]`, `icon`.
- [ ] WebView avec `NetworkSession`/stockage isolé par app-id (concept déjà esquissé dans `wikissb.js`).
- [ ] Politique de navigation : liens hors `allowed_domains` → ouverts dans le navigateur système
      (logique `decide-policy` déjà présente, à rendre paramétrable).
- [ ] Persistance fenêtre (taille/position), titre dynamique = `<title>` de la page.
- [ ] Gestion : notifications, téléchargements, permissions (caméra/micro/géoloc) configurables.
- [ ] Zoom, raccourcis clavier de base, menu contextuel minimal.
- [ ] (Option) injection de CSS/JS custom par Site (ex. masquer un bandeau).

### 3.2 Format & système de soumission d'un Site (`/sites`)
Un dossier par Site : `sites/<io.bigbrowser.NomDuSite>/`.

Manifeste minimal `site.yml` :
```yaml
# Champs requis
id: io.bigbrowser.MonSite        # ID reverse-DNS (= app-id Flatpak)
title: Mon Site                  # nom affiché
url: https://app.example.com     # URL de la webapp
icon: icon.svg                   # fichier dans le dossier (svg ou png ≥256²)

# Métadonnées inspirées de Flathub (AppStream)
summary: Résumé en une ligne
description: |
  Description longue, markdown léger.
categories: [Network, Productivity]   # catégories AppStream/freedesktop
developer_name: Nom du dev / orga
project_license: MIT             # licence de la webapp si connue, sinon "LicenseRef-proprietary"
homepage: https://example.com
screenshots:
  - screenshots/1.png
keywords: [chat, mail]

# Comportement du Site (optionnel)
allowed_domains: [app.example.com, cdn.example.com]
permissions: { notifications: true, geolocation: false }
```

- [ ] Définir le **schéma JSON Schema** du manifeste (validation automatique).
- [ ] Convention d'arborescence (`site.yml`, `icon.svg`, `screenshots/`).
- [ ] `CONTRIBUTING.md` : guide pas-à-pas de soumission + template de PR.
- [ ] Template d'*Issue* "Proposer un Site" pour non-techniciens (génère un brouillon de PR).

### 3.3 Tooling de build (`/tooling`)
Un CLI (Node ou Python) qui transforme un `site.yml` en artefacts Flatpak.

- [ ] `validate` : vérifie le manifeste contre le JSON Schema + ID unique + URL/icône valides.
- [ ] `generate` : produit pour chaque Site
  - `<id>.flatpak.yml` (manifeste flatpak-builder : module Engine partagé + le `site.json`),
  - `<id>.metainfo.xml` (AppStream : nom, résumé, description, screenshots, catégories, licence),
  - `<id>.desktop` (Exec = Engine, Icon, Categories),
  - icônes redimensionnées (hicolor 64/128/256).
- [ ] `build` : appelle `flatpak-builder` localement (pour tester) → `.flatpak` bundle.
- [ ] Tests : un faux manifeste → vérifie les artefacts générés.

### 3.4 Système de build Flatpak (CI)
- [ ] Image/Action avec `flatpak`, `flatpak-builder`, runtimes `org.gnome.Platform//<ver>` + SDK.
- [ ] Chaque Site embarque l'Engine via le module partagé `/engine` (cf. décision d'archi §2) ;
      OSTree déduplique le binaire entre tous les Sites.
- [ ] Build matriciel : un Site modifié dans la PR → uniquement celui-ci est rebâti (diff `sites/`).
- [ ] **Rebuild global déclenché si `/engine` change** : tous les Sites rebâtis pour intégrer
      le nouvel Engine (copié au build, pas au runtime).
- [ ] Vérifications qualité : `flatpak run org.freedesktop.appstream-glib validate` sur le metainfo,
      `desktop-file-validate`, lint icône.
- [ ] Publication d'artefacts de test (`.flatpak`) sur la PR pour essai manuel.

### 3.5 Big Browser Hub — publication (OSTree statique sur GitHub Pages)
- [ ] Générer le dépôt OSTree signé (clé GPG) :
      `flatpak build-export --gpg-sign=<KEY> repo/ <build>` puis `flatpak build-update-repo`.
      La clé privée GPG vit dans un **secret GitHub Actions** ; la clé publique est distribuée
      dans le `.flatpakrepo`.
- [ ] **Publication sur GitHub Pages** : la CI pousse le dossier `repo/` sur la branche
      `gh-pages` (ou un dépôt dédié `*-repo`). Pages sert le tout en HTTPS.
- [ ] Générer `bigbrowser.flatpakrepo` (URL du repo + clé GPG publique, pour `flatpak remote-add`)
      et un `.flatpakref` par Site (install en un clic depuis le navigateur).
- [ ] Catalogue web statique (`/catalog`) listant les Sites (lecture des `site.yml`) :
      titre, icône, résumé, screenshots, bouton "Installer" (`.flatpakref`) + commande CLI.
- [ ] Doc utilisateur (cf. section 2).
- **Limites GitHub Pages** : ~1 Go de dépôt recommandé, 100 Go/mois de bande passante.
  Suffisant pour le MVP. Si dépassement :
  - bundles `.flatpak` volumineux → **GitHub Releases** (2 Go/fichier),
  - gros catalogue → **object storage** (Cloudflare R2 / S3) + éventuellement **flat-manager**.

---

## 4. Phases de réalisation

### Phase 0 — Fondations (préparer le terrain)
- [ ] Initialiser le dépôt git (actuellement non versionné), `README`, licence, structure monorepo.
- [ ] Réserver le namespace `io.bigbrowser.*` (domaine/org GitHub) et fixer l'URL Pages du Hub.
- [x] Identité tranchée : projet **Big Browser**, unité = **Site**, moteur = **Engine**.
- [x] Stack Engine tranchée : **GTK4 + WebKitGTK 6.0**.
- [x] Hébergement tranché : **dépôt OSTree statique sur GitHub Pages** (branche `gh-pages`).
- [ ] Activer GitHub Pages sur le dépôt, générer la paire de clés GPG, stocker la privée en secret.

### Phase 1 — Engine paramétrable (MVP technique)
- [x] Refactor `wikissb.js` → `engine/bigbrowser.js` (GTK4/WebKit6) lisant un manifeste externe.
- [x] Manifestes d'exemple (`examples/wikipedia.site.json`, `examples/excalidraw.site.json`).
- [x] Testé en local sur l'hôte (Wikipédia s'affiche). NB : la toolbox a un trust store vide
      → dev sur l'hôte ou cf. contournement TLS dans `engine/README.md`.
- **✅ Jalon atteint : `gjs engine/bigbrowser.js examples/wikipedia.site.json` ouvre la webapp.**

### Phase 2 — Empaquetage Flatpak d'un Site (à la main)
- [x] Manifeste flatpak-builder + module Engine partagé (`sites/io.bigbrowser.Wikipedia/`).
- [x] metainfo.xml + .desktop + icône + `build.sh` écrits à la main.
- [x] Build + install local validés (`--disable-rofiles-fuse` requis en conteneur/CI).
- **✅ Jalon atteint : `flatpak run io.bigbrowser.Wikipedia` ouvre le Site empaqueté.**

### Phase 3 — Tooling de génération
- [x] CLI `tooling/bbhub.py` : `validate` + `generate` + `build` à partir de `site.yaml`.
- [x] JSON Schema de référence (`tooling/site.schema.json`) + validation manuelle intégrée.
- [x] Site Wikipédia converti au format source unique (`site.yaml` + `icon.svg`).
- [x] Artefacts générés validés : `appstreamcli validate` ✓, `desktop-file-validate` ✓.
- [x] Build depuis les artefacts générés validé (équivalence avec le build manuel Phase 2).
- **✅ Jalon atteint : un seul `site.yaml` produit tous les artefacts Flatpak.**

### Phase 4 — CI/CD GitHub Actions
- [x] Workflow PR (`ci.yml`) : matrice par Site → validate + generate + lint + build.
- [x] Workflow publish (`publish.yml`) : build → OSTree signé GPG → catalogue → GitHub Pages.
- [x] `tooling/catalog.py` : `index.html` + `bigbrowser.flatpakrepo` + `.flatpakref` par Site.
- [x] README racine : mise en route Pages + secrets GPG.
- [ ] Brancher sur un vrai dépôt GitHub : activer Pages, poser les secrets, premier run.
- **Jalon : merger une PR publie automatiquement le Site sur le Hub (à vérifier en réel).**

### Phase 5 — Hub & catalogue public
- [ ] Signer et héberger le repo OSTree, générer `bigbrowser.flatpakrepo` + `.flatpakref`.
- [ ] Site catalogue statique sur GitHub Pages.
- **Jalon : un inconnu peut ajouter le remote et installer un Site en 1 clic.**

### Phase 6 — Soumission communautaire & gouvernance
- [ ] `CONTRIBUTING.md`, templates Issue/PR, CODEOWNERS, règles de revue.
- [ ] Politique de modération (Sites interdits, marques, licences).
- **Jalon : une première contribution externe est mergée et publiée.**

### Phase 7 — Durcissement & finitions (post-MVP)
- [ ] Sandbox Flatpak au plus juste (réseau, pas d'accès FS hôte inutile).
- [ ] Mises à jour automatiques d'icônes/métadonnées, versionnage des Sites.
- [ ] Statistiques d'install, page de signalement, gestion des Sites obsolètes.
- [ ] Migration vers flat-manager si le volume grandit.

---

## 5. Risques & points d'attention

| Sujet | Risque | Mitigation |
|-------|--------|------------|
| WebKit | Réécriture API GTK3→GTK4/WebKit6 | Faite une fois dans l'Engine (cf. note migration §2) |
| Sandbox | Sites nécessitant notif/géoloc/persistance | Permissions Flatpak explicites + finish-args minimal |
| Marques/légal | Icônes & noms de tiers redistribués | Namespace `io.bigbrowser.*` + politique de soumission/revue, licences claires |
| Signature repo | Clé GPG à protéger | Secret GitHub Actions, jamais en clair |
| Taille du dépôt OSTree | Faible : Sites = métadonnées, dédup OSTree | Module Engine partagé + WebKit hors-repo ; Pages largement suffisant |
| MAJ de l'Engine | Script copié au build → rebuild de tous les Sites | Rebuild matriciel automatisé en CI sur changement `/engine` |
| Unicité des IDs | Collisions d'app-id | Validation CI (ID `io.bigbrowser.*` unique) |

---

## 6. Premières actions concrètes (cette semaine)

1. `git init` + structure de dossiers (`/engine`, `/sites`, `/tooling`, `/catalog`) + README.
2. Migrer `wikissb.js` → `engine/bigbrowser.js` paramétrable (GTK4/WebKit6) lisant un `site.json`.
3. Empaqueter un premier Site en Flatpak à la main pour valider la chaîne.
4. Rédiger le JSON Schema de `site.yml`.

---

*Document de cadrage — à itérer au fil du projet.*
