# BigBrowser Applications Suite

Cette suite permet de générer automatiquement des applications Flatpak basées sur BigBrowser pour tous les services web définis dans `flatpak_apps.json`.

## 🎯 Vue d'ensemble

**BigBrowser** est un navigateur web simple basé sur Deno qui utilise WebView. Cette suite permet de créer des applications dédiées pour chaque service web, chacune ayant :
- Sa propre icône et identité
- Son URL spécifique pré-configurée  
- Son intégration complète au système (menu, associations de fichiers)
- Son package Flatpak distributable

## 📊 Applications disponibles

**Applications générées avec succès :**
- 🔍 **Google Search** - Recherche web avec Google
- 📝 **Notion** - Espace de travail tout-en-un
- 🎨 **SketchUp** - Modélisation 3D
- 📺 **YouTube** - Plateforme vidéo
- 📧 **Gmail** - Email par Google
- 📅 **Google Calendar** - Calendrier
- 🎨 **Figma** - Outil de design collaboratif
- 🐙 **GitHub** - Plateforme de développement
- 🤖 **ChatGPT** - Assistant IA d'OpenAI
- 🎬 **Netflix** - Streaming vidéo
- 🎨 **Canva** - Design graphique
- ✍️ **Medium** - Plateforme de blogging
- 📌 **Pinterest** - Découverte d'idées
- 🎵 **TikTok** - Vidéos courtes

**Total : 14 applications prêtes**

## 🚀 Utilisation rapide

### Construction automatique de toutes les applications
```bash
./build-all-apps.sh
```

### Installation locale de toutes les applications
```bash
./install-all-apps.sh
```

### Export vers fichiers .flatpak
```bash
./export-all-apps.sh
```

## 📋 Scripts disponibles

| Script | Description |
|--------|-------------|
| `generate-app-manifests.py` | Génère les manifestes Flatpak depuis `flatpak_apps.json` |
| `build-all-apps.sh` | Construit toutes les applications Flatpak |
| `install-all-apps.sh` | Installe toutes les applications localement |
| `export-all-apps.sh` | Exporte toutes les applications vers des fichiers .flatpak |

## 🎯 Flux de travail complet

1. **Générer les manifestes :**
   ```bash
   python3 generate-app-manifests.py
   ```

2. **Construire toutes les applications :**
   ```bash
   ./build-all-apps.sh
   ```

3. **Installer pour tester :**
   ```bash
   ./install-all-apps.sh
   ```

4. **Utiliser les applications :**
   ```bash
   flatpak run com.tekkengreg.bigbrowser.youtube
   flatpak run com.tekkengreg.bigbrowser.github
   flatpak run com.tekkengreg.bigbrowser.notion
   ```

5. **Exporter pour distribution :**
   ```bash
   ./export-all-apps.sh
   ```

## 🗂️ Structure du projet

```
├── bigbrowser                           # Exécutable Deno principal
├── flatpak_apps.json                   # Configuration des applications
├── icons/                              # Icônes des applications
│   ├── google.png
│   ├── youtube.png
│   └── ...
├── manifests/                          # Manifestes Flatpak générés
│   ├── com.tekkengreg.bigbrowser.google.yml
│   ├── com.tekkengreg.bigbrowser.youtube.yml
│   └── ...
├── dist/                               # Fichiers .flatpak distribués
│   ├── google.flatpak
│   ├── youtube.flatpak
│   └── ...
└── build-dir-*/                       # Répertoires de construction temporaires
```

## ⚙️ Personnalisation

### Ajouter une nouvelle application

1. **Ajouter l'entrée dans `flatpak_apps.json` :**
   ```json
   "myapp": {
     "appName": "myapp",
     "displayName": "My Application",
     "description": "Description de mon app",
     "url": "https://myapp.com",
     "categories": "Category;SubCategory;",
     "keywords": "keyword1;keyword2;keyword3;"
   }
   ```

2. **Ajouter l'icône `icons/myapp.png`**

3. **Regénérer :**
   ```bash
   ./build-all-apps.sh
   ```

### Modifier une application existante

1. Modifier `flatpak_apps.json`
2. Éventuellement remplacer l'icône
3. Reconstruire avec `./build-all-apps.sh`

## 🔧 Configuration technique

- **Runtime :** GNOME Platform 48 (inclut WebKitGTK)
- **Sandbox :** Permissions complètes pour navigation web
- **Architecture :** x86_64
- **Taille par app :** ~22MB (incluant le runtime partagé)

## 🎨 Icônes

Les icônes doivent être :
- **Format :** PNG
- **Taille :** 128x128 pixels minimum
- **Nom :** Identique au nom de l'app dans `flatpak_apps.json`
- **Emplacement :** `icons/{appname}.png`

## 📦 Distribution

Les fichiers `.flatpak` générés dans le dossier `dist/` peuvent être :
- Installés sur n'importe quel système Linux avec Flatpak
- Distribués via des dépôts Flatpak
- Partagés directement entre utilisateurs

**Installation d'un fichier .flatpak :**
```bash
flatpak install --user dist/youtube.flatpak
```

## 🛠️ Dépannage

### Icônes manquantes
Si des applications sont ignorées lors de la génération :
1. Vérifiez que le fichier `icons/{appname}.png` existe
2. Vérifiez les permissions de lecture du fichier
3. Relancez `python3 generate-app-manifests.py`

### Erreurs de construction
Si une construction échoue :
1. Vérifiez que les runtimes GNOME sont installés :
   ```bash
   flatpak install flathub org.gnome.Platform//48 org.gnome.Sdk//48
   ```
2. Nettoyez les caches : `rm -rf .flatpak-builder/`
3. Relancez la construction

### Applications qui ne se lancent pas
Si une application crash au lancement :
1. Testez l'exécutable principal : `./bigbrowser https://example.com`
2. Vérifiez les logs : `flatpak run --log-level=debug com.tekkengreg.bigbrowser.appname`
3. Vérifiez les permissions dans le manifeste

## 📈 Statistiques

- **Applications totales dans flatpak_apps.json :** 40
- **Applications avec icônes disponibles :** 14  
- **Applications construites avec succès :** 14
- **Taux de succès :** 100% (pour les apps avec icônes)

## 🎉 Résultats

Vous disposez maintenant d'une suite complète de 14 applications web natives pour Linux, toutes basées sur votre navigateur BigBrowser, packagees et prêtes à être distribuées via Flatpak ! 