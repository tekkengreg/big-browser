# BigBrowser avec Repository Local

Guide complet pour utiliser BigBrowser avec un repository Flatpak local.

## 🎯 Avantages du Repository Local

- **Gestion centralisée** : Toutes les applications dans un seul repository
- **Mises à jour simplifiées** : `flatpak update` met à jour toutes les apps
- **Distribution locale** : Partage facile sur le réseau local
- **Intégration native** : Applications gérées comme des packages Flatpak standards

## 📊 État Actuel

**Applications disponibles dans le repository local :**
- ✅ **GitHub** - Plateforme de développement
- ✅ **Gmail** - Email par Google  
- ✅ **Google Calendar** - Calendrier
- ✅ **Medium** - Plateforme de blogging
- ✅ **Netflix** - Streaming vidéo
- ✅ **TikTok** - Vidéos courtes
- ✅ **YouTube** - Plateforme vidéo

**Total : 7 applications fonctionnelles**

## 🚀 Workflow Complet

### 1. Construction et Configuration
```bash
# Construction de toutes les applications + configuration du repository local
./build-all-apps.sh
```
Ce script :
- Génère les manifestes depuis `flatpak_apps.json`
- Construit toutes les applications Flatpak
- Configure automatiquement le repository local
- Exporte toutes les applications vers `local-repo/`

### 2. Installation depuis le Repository Local
```bash
# Nettoyage et installation depuis le repository local
./clean-and-install-from-local.sh
```
Ce script :
- Désinstalle les versions existantes (si nécessaire)
- Configure le remote `local-bigbrowser`
- Installe toutes les applications depuis le repository local

### 3. Workflow Automatique Complet
```bash
# Tout automatique de A à Z
./workflow-complete.sh
```

## 🗂️ Structure du Repository Local

```
local-repo/                             # Repository OSTree
├── config                             # Configuration du repository
├── objects/                           # Objets OSTree (applications)
├── refs/                              # Références des branches
└── summary                            # Métadonnées du repository

Repository configuré comme remote:
- **Nom:** local-bigbrowser
- **Type:** file:///path/to/local-repo
- **Mode:** --no-gpg-verify (local, pas de signature)
```

## 🎯 Utilisation

### Lancer une Application
```bash
flatpak run com.tekkengreg.bigbrowser.github
flatpak run com.tekkengreg.bigbrowser.youtube
flatpak run com.tekkengreg.bigbrowser.netflix
```

### Gestion du Repository Local

**Lister les applications disponibles :**
```bash
flatpak remote-ls local-bigbrowser
```

**Voir les applications installées :**
```bash
flatpak list --app | grep bigbrowser
```

**Mettre à jour :**
```bash
flatpak update
```

**Ajouter le repository sur un autre système :**
```bash
flatpak remote-add --user --no-gpg-verify local-bigbrowser file:///path/to/local-repo
```

## 🔧 Gestion Avancée

### Ajouter une Nouvelle Application

1. **Ajouter l'entrée dans `flatpak_apps.json`**
2. **Ajouter l'icône `icons/appname.png`**
3. **Reconstruire et mettre à jour :**
   ```bash
   ./build-all-apps.sh
   flatpak update
   ```

### Partager le Repository sur le Réseau

**Via serveur HTTP simple :**
```bash
cd local-repo
python3 -m http.server 8080
```

**Sur les clients :**
```bash
flatpak remote-add --user --no-gpg-verify shared-bigbrowser http://IP-SERVEUR:8080
```

### Synchronisation entre Machines

**Copier le repository :**
```bash
rsync -av local-repo/ autre-machine:/path/to/local-repo/
```

## 📈 Statistiques

- **Repository :** `local-repo/` (~150MB)
- **Remote configuré :** `local-bigbrowser`
- **Applications disponibles :** 14 (dans le repository)
- **Applications installées :** 7 (fonctionnelles)
- **Architecture :** x86_64
- **Runtime :** GNOME Platform 48

## 🛠️ Dépannage

### Repository Non Trouvé
```bash
# Vérifier l'existence
ls -la local-repo/

# Recréer si nécessaire
./setup-local-repo.sh
```

### Applications Non Installées
```bash
# Forcer le nettoyage et la réinstallation
./clean-and-install-from-local.sh
```

### Remote Non Configuré
```bash
# Ajouter manuellement
flatpak remote-add --user --no-gpg-verify local-bigbrowser file://$(pwd)/local-repo
```

### Mettre à Jour le Repository
```bash
# Après reconstruction des applications
./setup-local-repo.sh
flatpak update --appstream local-bigbrowser
```

## 🎉 Avantages Obtenus

✅ **Repository local fonctionnel** avec 7 applications  
✅ **Gestion native via Flatpak** (update, list, install, uninstall)  
✅ **Applications intégrées au système** (menu, icônes, associations)  
✅ **Distribution simplifiée** (copie du dossier local-repo)  
✅ **Workflow automatisé** complet  
✅ **Extensibilité** facile (ajout de nouvelles applications)  

Le système BigBrowser avec repository local est maintenant opérationnel ! 🚀 