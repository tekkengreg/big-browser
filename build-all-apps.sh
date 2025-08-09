#!/bin/bash

# Script pour construire toutes les applications Flatpak à partir des manifests sous packages/apps

set -e

echo "=== Construction de toutes les applications BigBrowser ==="

# Migrer les manifests (packages/apps) pour utiliser le runtime Tauri si le script existe
# if [ -f "migrate-packages-apps-to-runtime.ts" ]; then
#   echo "Migration des manifests (packages/apps) vers le runtime Tauri..."
#   deno run -A migrate-packages-apps-to-runtime.ts
# fi

# Vérifier la présence du runtime construit
if [ ! -f "build-dir-tauri-runtime/files/bin/tauri-runtime" ]; then
  echo "Erreur: le binaire du runtime est manquant ('build-dir-tauri-runtime/files/bin/tauri-runtime')."
  echo "Veuillez construire le runtime d'abord: ./build-tauri-runtime.sh"
  exit 1
fi

echo ""
echo "Construction des Flatpaks..."

# Compter les manifestes
manifest_count=$(find packages/apps -mindepth 2 -maxdepth 2 -name "manifest.yml" | wc -l)
echo "Nombre d'applications à construire: $manifest_count"

built_count=0
failed_count=0

# Construire chaque application
for manifest in packages/apps/*/manifest.yml; do
    app_dir=$(dirname "$manifest")
    short_name=$(basename "$app_dir")
    app_id="com.tekkengreg.bigbrowser.${short_name}"

    echo ""
    echo "📦 Construction de $app_id..."

    build_dir="build-dir-${short_name}"

    if flatpak-builder --force-clean "$build_dir" "$manifest"; then
        echo "✅ $app_id construit avec succès"
        built_count=$((built_count + 1))
    else
        echo "❌ Échec de la construction de $app_id"
        failed_count=$((failed_count + 1))
    fi
done

echo ""
echo "=== Résumé de la construction ==="
echo "✅ Applications construites: $built_count"
echo "❌ Échecs: $failed_count"
echo "📦 Total: $((built_count + failed_count))"

echo ""
echo "🚀 Mise à jour du repository local..."
./setup-local-repo.sh

echo ""
echo "Prochaines étapes:"
echo "  ./install-from-local-repo.sh    # Installer depuis le repository local"
echo "  ./export-all-apps.sh           # Exporter vers des fichiers .flatpak" 