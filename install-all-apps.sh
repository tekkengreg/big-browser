#!/bin/bash

# Script pour installer toutes les applications Flatpak localement

set -e

echo "=== Installation locale de toutes les applications BigBrowser ==="

installed_count=0
failed_count=0

# Installer chaque application construite
for manifest in manifests/com.tekkengreg.bigbrowser.*.yml; do
    # Extraire le nom de l'app du fichier manifeste
    app_name=$(basename "$manifest" .yml)
    
    # Ignorer le manifeste principal
    if [[ "$app_name" == "com.tekkengreg.bigbrowser" ]]; then
        continue
    fi
    
    # Nom du répertoire de build
    build_dir="build-dir-${app_name##*.}"
    
    # Vérifier que le répertoire de build existe
    if [ ! -d "$build_dir" ]; then
        echo "⚠️  IGNORÉ: $app_name (répertoire de build manquant: $build_dir)"
        echo "   Construisez d'abord avec: ./build-all-apps.sh"
        failed_count=$((failed_count + 1))
        continue
    fi
    
    echo "📦 Installation de $app_name..."
    
    # Installer l'application
    if flatpak-builder --user --install --force-clean "$build_dir" "$manifest" > /dev/null 2>&1; then
        echo "✅ $app_name installé avec succès"
        installed_count=$((installed_count + 1))
    else
        echo "❌ Échec de l'installation de $app_name"
        failed_count=$((failed_count + 1))
    fi
done

echo ""
echo "=== Résumé de l'installation ==="
echo "✅ Applications installées: $installed_count"
echo "❌ Échecs: $failed_count"
echo "📦 Total: $((installed_count + failed_count))"

if [ $installed_count -gt 0 ]; then
    echo ""
    echo "🎉 Applications installées avec succès !"
    echo ""
    echo "Vous pouvez maintenant utiliser vos applications:"
    echo "  flatpak run com.tekkengreg.bigbrowser.google"
    echo "  flatpak run com.tekkengreg.bigbrowser.youtube"
    echo "  flatpak run com.tekkengreg.bigbrowser.github"
    echo "  etc..."
    echo ""
    echo "Pour voir toutes les applications installées:"
    echo "  flatpak list --app | grep bigbrowser"
fi 