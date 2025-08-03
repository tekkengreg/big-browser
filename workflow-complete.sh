#!/bin/bash

# Workflow complet pour BigBrowser - De la construction à l'installation

set -e

echo "=============================================="
echo "🚀 WORKFLOW COMPLET BIGBROWSER FLATPAK"
echo "=============================================="
echo ""

# Étape 1: Vérifications préliminaires
echo "📋 ÉTAPE 1: Vérifications préliminaires"
echo "=============================================="

if [ ! -f "bigbrowser" ]; then
    echo "❌ Erreur: L'exécutable 'bigbrowser' n'existe pas."
    echo "   Créez d'abord l'exécutable avec: deno compile -A main.ts"
    exit 1
fi

if [ ! -f "flatpak_apps.json" ]; then
    echo "❌ Erreur: flatpak_apps.json n'existe pas."
    exit 1
fi

echo "✅ Exécutable BigBrowser trouvé ($(du -h bigbrowser | cut -f1))"
echo "✅ Configuration des applications trouvée"

# Compter les applications avec icônes
apps_with_icons=$(python3 -c "
import json
import os
with open('flatpak_apps.json') as f:
    apps = json.load(f)
count = sum(1 for app in apps if os.path.exists(f'icons/{app}.png'))
total = len(apps)
print(f'{count}/{total}')
")

echo "✅ Applications avec icônes: $apps_with_icons"
echo ""

# Étape 2: Construction
echo "📦 ÉTAPE 2: Construction des applications"
echo "=============================================="
./build-all-apps.sh
echo ""

# Étape 3: Installation depuis le repository local
echo "💾 ÉTAPE 3: Installation depuis le repository local"
echo "=============================================="
./install-from-local-repo.sh
echo ""

# Étape 4: Vérification
echo "✅ ÉTAPE 4: Vérification des installations"
echo "=============================================="

installed_apps=$(flatpak list --app | grep bigbrowser | wc -l)
echo "📊 Applications BigBrowser installées: $installed_apps"

if [ $installed_apps -gt 0 ]; then
    echo ""
    echo "📋 Applications disponibles:"
    flatpak list --app | grep bigbrowser | awk '{print "  - " $2 " (" $1 ")"}'
fi

echo ""

# Étape 5: Export (optionnel)
echo "📤 ÉTAPE 5: Export des fichiers .flatpak (optionnel)"
echo "=============================================="
read -p "Voulez-vous exporter les applications vers des fichiers .flatpak ? (y/N): " export_choice

if [[ "$export_choice" =~ ^[Yy]$ ]]; then
    ./export-all-apps.sh
    echo ""
    echo "📁 Fichiers .flatpak créés dans le dossier 'dist/':"
    ls -lh dist/*.flatpak 2>/dev/null | awk '{print "  - " $9 " (" $5 ")"}'
else
    echo "⏭️  Export ignoré"
fi

echo ""
echo "=============================================="
echo "🎉 WORKFLOW COMPLET TERMINÉ !"
echo "=============================================="
echo ""
echo "📊 RÉSUMÉ FINAL:"
echo "  Repository local:     local-repo/"
echo "  Applications installées: $installed_apps"
echo "  Remote configuré:     local-bigbrowser"
echo ""
echo "🎯 UTILISATION:"
echo "  flatpak run com.tekkengreg.bigbrowser.google"
echo "  flatpak run com.tekkengreg.bigbrowser.youtube"
echo "  flatpak run com.tekkengreg.bigbrowser.github"
echo ""
echo "🔧 GESTION:"
echo "  flatpak list --app | grep bigbrowser    # Lister les apps"
echo "  flatpak update                          # Mettre à jour"
echo "  flatpak uninstall com.tekkengreg.bigbrowser.APPNAME  # Désinstaller"
echo ""
echo "📂 REPOSITORY LOCAL:"
echo "  Emplacement: $(pwd)/local-repo"
echo "  Remote name: local-bigbrowser"
echo "  Type: file://$(pwd)/local-repo" 