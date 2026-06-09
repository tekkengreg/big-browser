#!/bin/bash

set -e

echo "=== Export BigBrowser Runtime (Tauri) vers fichier .flatpak ==="

# Vérifier que l'application est construite
if [ ! -d "build-dir-tauri-runtime" ]; then
    echo "❌ Erreur: Le dossier de build n'existe pas"
    echo "Construisez d'abord l'application avec: ./build-tauri-runtime.sh"
    exit 1
fi

# Créer le dossier d'export s'il n'existe pas
mkdir -p export-repo

echo "📦 Export vers repository local..."
flatpak build-export export-repo build-dir-tauri-runtime

echo "📦 Création du fichier .flatpak..."
flatpak build-bundle export-repo tauri-runtime.flatpak com.tekkengreg.bigbrowser.runtime

if [ $? -eq 0 ]; then
    echo "✅ Export réussi!"
    echo ""
    echo "📁 Fichier créé: tauri-runtime.flatpak"
    echo "📊 Taille: $(du -h tauri-runtime.flatpak | cut -f1)"
    echo ""
    echo "🚀 Pour installer sur un autre système:"
    echo "   flatpak install --user tauri-runtime.flatpak"
    echo ""
    echo "🚀 Pour lancer l'application après installation:"
    echo "   flatpak run com.tekkengreg.bigbrowser.runtime"
    echo "   flatpak run com.tekkengreg.bigbrowser.runtime https://www.example.com"
else
    echo "❌ Erreur lors de l'export"
    exit 1
fi 