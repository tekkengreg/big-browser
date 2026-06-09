#!/bin/bash

# Script pour construire le Flatpak BigBrowser

set -e

echo "=== Construction du Flatpak BigBrowser ==="

# Vérifier que l'exécutable existe
if [ ! -f "bigbrowser" ]; then
    echo "Erreur: L'exécutable 'bigbrowser' n'existe pas."
    echo "Veuillez d'abord créer l'exécutable avec Deno."
    exit 1
fi

# Vérifier que l'icône existe
if [ ! -f "icons/bigbrowser.png" ]; then
    echo "Erreur: L'icône 'icons/bigbrowser.png' n'existe pas."
    exit 1
fi

# Créer le répertoire de construction s'il n'existe pas
mkdir -p build-dir-bigbrowser

echo "Construction du Flatpak..."

# Construire le Flatpak
flatpak-builder --force-clean build-dir-bigbrowser manifests/com.tekkengreg.bigbrowser.yml

echo "Installation locale du Flatpak..."

# Installer localement le Flatpak pour les tests
flatpak-builder --user --install --force-clean build-dir-bigbrowser manifests/com.tekkengreg.bigbrowser.yml

echo "=== Construction terminée ==="
echo ""
echo "Vous pouvez maintenant lancer BigBrowser avec :"
echo "flatpak run com.tekkengreg.bigbrowser"
echo ""
echo "Ou l'exporter vers un fichier .flatpak avec :"
echo "flatpak build-export repo build-dir-bigbrowser"
echo "flatpak build-bundle repo bigbrowser.flatpak com.tekkengreg.bigbrowser" 