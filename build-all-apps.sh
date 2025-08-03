#!/bin/bash

# Script pour construire toutes les applications Flatpak depuis flatpak_apps.json

set -e

echo "=== Construction de toutes les applications BigBrowser ==="

# Vérifier que le générateur existe
if [ ! -f "generate-app-manifests.py" ]; then
    echo "Erreur: generate-app-manifests.py n'existe pas"
    exit 1
fi

# Vérifier que l'exécutable existe
if [ ! -f "bigbrowser" ]; then
    echo "Erreur: L'exécutable 'bigbrowser' n'existe pas."
    echo "Veuillez d'abord créer l'exécutable avec Deno."
    exit 1
fi

# Générer tous les manifestes
echo "Génération des manifestes..."
python3 generate-app-manifests.py

echo ""
echo "Construction des Flatpaks..."

# Compter les manifestes générés
manifest_count=$(find manifests/ -name "*.yml" -not -name "com.tekkengreg.bigbrowser.yml" | wc -l)
echo "Nombre d'applications à construire: $manifest_count"

built_count=0
failed_count=0

# Construire chaque application
for manifest in manifests/com.tekkengreg.bigbrowser.*.yml; do
    # Extraire le nom de l'app du fichier manifeste
    app_name=$(basename "$manifest" .yml)
    
    # Ignorer le manifeste principal
    if [[ "$app_name" == "com.tekkengreg.bigbrowser" ]]; then
        continue
    fi
    
    echo ""
    echo "📦 Construction de $app_name..."
    
    # Nom du répertoire de build
    build_dir="build-dir-${app_name##*.}"
    
    # Construire l'application
    if flatpak-builder --force-clean "$build_dir" "$manifest"; then
        echo "✅ $app_name construit avec succès"
        built_count=$((built_count + 1))
    else
        echo "❌ Échec de la construction de $app_name"
        failed_count=$((failed_count + 1))
    fi
done

echo ""
echo "=== Résumé de la construction ==="
echo "✅ Applications construites: $built_count"
echo "❌ Échecs: $failed_count"
echo "📦 Total: $((built_count + failed_count))"

if [ $failed_count -eq 0 ]; then
    echo ""
    echo "🎉 Toutes les applications ont été construites avec succès !"
    echo ""
    echo "🚀 Configuration du repository local..."
    ./setup-local-repo.sh
    echo ""
    echo "Prochaines étapes:"
    echo "  ./install-from-local-repo.sh    # Installer depuis le repository local"
    echo "  ./export-all-apps.sh           # Exporter vers des fichiers .flatpak"
else
    echo ""
    echo "⚠️  Certaines constructions ont échoué. Vérifiez les erreurs ci-dessus."
fi 