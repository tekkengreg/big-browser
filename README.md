# Flatpak

## command pnppm

```sh
# Générer toutes les applications avec icônes
pnpm run generate-apps

# Générer les applications sans icônes (mode offline)
pnpm run generate-apps-offline

# Mettre à jour uniquement les icônes
pnpm run update-icons

# Mettre à jour les métadonnées du repository (version propre)
pnpm run update-repo

# Mettre à jour avec détails complets (version verbose)
pnpm run update-repo-verbose

# Déployer toutes les applications (génération + mise à jour repo)
pnpm run deploy

# Vérifier les mises à jour disponibles (sans installer)
pnpm run check-updates
```

## Créer un dépôt local 

```sh
flatpak remote-add --user --no-gpg-verify local-repo file:///home/tekkengreg/Workspace/big-browser/repo
```

## Ajout d'un dépôt local

```sh
flatpak remote-add --user --no-gpg-verify local-repo ./repo
```

## Supprimer et recréer le dépôt local :

```sh
flatpak remote-delete --user local-repo
```

## Gestion

```sh
# Lister vos apps installées
flatpak list --app | grep tekkengreg

# Mettre à jour toutes les applications
flatpak update

# Mettre à jour une application spécifique
flatpak update com.tekkengreg.bigbrowser.google

# Désinstaller
flatpak uninstall com.tekkengreg.bigbrowser.google
```

## Workflow des mises à jour

### Pour déployer des nouvelles versions :

```sh
# 1. Déploiement complet (recommandé)
pnpm run deploy

# 2. Ou étape par étape :
pnpm run generate-apps  # Régénère avec nouvelles icônes/configs
pnpm run update-repo    # Met à jour le repository
```

### Pour les utilisateurs finaux :

```sh
# Vérifier les applications installées
pnpm run check-updates

# Installer les mises à jour
flatpak update
```

```sh
flatpak list --app                    # Toutes les apps installées
flatpak list --app --user             # Apps installées pour l'utilisateur
flatpak list --app --system           # Apps installées système
flatpak remotes                       # Liste des dépôts configurés
flatpak build-update-repo repo        # Régénère les métadonnées du dépôt (fix erreurs summaries)
flatpak remote-ls local-repo          # Apps disponibles dans local-repo
flatpak remote-ls notion-repo         # Apps disponibles dans notion-repo
```

## get pakcage size
```sh
echo "📊 MÉTHODE 2 : Taille des répertoires d'installation Flatpak" && echo "============================================================" && echo "" && echo "🏠 Répertoire Flatpak utilisateur :" && du -sh ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.* 2>/dev/null | sort -h

echo "📊 MÉTHODE 5 : Comparaison des tailles réelles" && echo "===============================================" && echo "" && echo "📁 Répertoires de build complets:" && du -sh build-dir-* | sort -h && echo "" && echo "📁 Application de base (détail):" && find build-dir-base -name "node_modules" -exec du -sh {} \; 2>/dev/null | head -3 && echo "" && echo "📊 Résumé des tailles d'installation Flatpak:" && du -sh ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.* | while read size path; do     app_name=$(basename "$path"); echo "  $app_name: $size"; done | sort -h


echo "📊 TAILLES DES APPLICATIONS FLATPAK" && echo "====================================" && echo "" && echo "🏗️  APPLICATION DE BASE:" && echo "   Taille d'installation: 906M" && echo "   Répertoire de build: 1.4G" && echo "" && echo "📱 APPLICATIONS LÉGÈRES:" && echo "   Google   - Installation: 15M  | Build: 60K" && echo "   Notion   - Installation: 15M  | Build: 68K" && echo "   SketchUp - Installation: 73M  | Build: 68K" && echo "" && echo "💡 EXPLICATION DES TAILLES:" && echo "   • Build = Taille des fichiers sources de l'app" && echo "   • Installation = Taille sur disque après installation Flatpak" && echo "   • Overhead Flatpak = ~15M minimum par application"

```

## Dépannage

### Erreur "Error: BigBrowser Base application is not installed"

Si vous obtenez cette erreur alors que l'application Base est installée :

**Problème :** Les scripts de vérification de dépendance utilisent `flatpak info` dans un sandbox qui ne peut pas accéder aux autres applications.

**Solution :** Les scripts utilisent maintenant `flatpak-spawn --host flatpak info` pour vérifier les dépendances.

### Erreur repository summaries

Si `flatpak remote-ls local-repo` échoue avec une erreur sur les fichiers summaries :

```sh
flatpak build-update-repo repo
``` 