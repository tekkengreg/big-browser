#!/bin/bash

# Script pour exporter le Flatpak BigBrowser vers un fichier .flatpak

set -e

echo "=== Export du Flatpak BigBrowser ==="

# Vérifier que le répertoire de construction existe
if [ ! -d "build-dir-bigbrowser" ]; then
    echo "Erreur: Le répertoire 'build-dir-bigbrowser' n'existe pas."
    echo "Veuillez d'abord construire le Flatpak avec './build-flatpak.sh'"
    exit 1
fi

# Créer le répertoire repo s'il n'existe pas
mkdir -p repo

echo "Export vers le repository..."

# Exporter vers le repository
flatpak build-export repo build-dir-bigbrowser

echo "Création du bundle .flatpak..."

# Créer le fichier .flatpak
flatpak build-bundle repo bigbrowser.flatpak com.tekkengreg.bigbrowser

echo "=== Export terminé ==="
echo ""
echo "Le fichier 'bigbrowser.flatpak' a été créé."
echo "Vous pouvez l'installer sur n'importe quel système avec :"
echo "flatpak install --user bigbrowser.flatpak"
echo ""
echo "Taille du fichier :"
ls -lh bigbrowser.flatpak 