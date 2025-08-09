#!/bin/bash

set -e

echo "=== Build script pour BigBrowser Runtime (Tauri) ==="

# Vérifications préalables
if [ ! -f "packages/runtimes/runtime/src-tauri/target/release/runtime" ]; then
    echo "❌ Erreur: l'exécutable Tauri runtime n'existe pas"
    echo "Construisez d'abord l'application avec: cd packages/runtimes/runtime && deno task tauri:build"
    exit 1
fi

if [ ! -f "icons/bigbrowser.png" ]; then
    echo "❌ Erreur: l'icône bigbrowser.png n'existe pas dans icons/"
    exit 1
fi

echo "✅ Exécutable Tauri trouvé: packages/runtimes/runtime/src-tauri/target/release/runtime"
echo "✅ Icône trouvée: icons/bigbrowser.png"

# Créer le dossier de build
BUILD_DIR="build-dir-tauri-runtime"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "📦 Construction du Flatpak Tauri Runtime..."

# Construction avec flatpak-builder
flatpak-builder --user --install --force-clean \
    "$BUILD_DIR" \
    "manifests/com.tekkengreg.bigbrowser.runtime.yml"

if [ $? -eq 0 ]; then
    echo "✅ Construction réussie!"
    echo ""
    echo "🚀 Pour tester l'application:"
    echo "   flatpak run com.tekkengreg.bigbrowser.runtime"
    echo "   flatpak run com.tekkengreg.bigbrowser.runtime https://www.example.com"
    echo ""
    echo "📦 Pour exporter vers un fichier .flatpak:"
    echo "   flatpak build-export export-repo $BUILD_DIR"
    echo "   flatpak build-bundle export-repo tauri-runtime.flatpak com.tekkengreg.bigbrowser.runtime"
else
    echo "❌ Erreur lors de la construction"
    exit 1
fi 