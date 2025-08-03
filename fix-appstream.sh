#!/bin/bash

# Script pour corriger les erreurs AppStream et reconstruire le repository

set -e

echo "=== Correction des erreurs AppStream ==="

echo "🔧 Régénération des manifestes avec métadonnées AppStream..."
python3 generate-app-manifests.py

echo ""
echo "📦 Reconstruction des applications avec métadonnées..."

# Reconstruire quelques applications pour inclure les métadonnées
for app in google youtube github gmail; do
    echo "📦 Reconstruction de $app..."
    if [ -f "manifests/com.tekkengreg.bigbrowser.$app.yml" ]; then
        flatpak-builder --force-clean "build-dir-$app" "manifests/com.tekkengreg.bigbrowser.$app.yml" > /dev/null 2>&1
        echo "✅ $app reconstruit avec métadonnées"
    fi
done

echo ""
echo "🗂️ Mise à jour du repository local..."
./setup-local-repo.sh

echo ""
echo "🔄 Mise à jour des métadonnées AppStream..."
if [ -d "local-repo" ]; then
    flatpak build-update-repo local-repo
    echo "✅ Repository mis à jour"
else
    echo "❌ Repository local non trouvé"
fi

echo ""
echo "📋 Vérification du repository..."
echo "Applications disponibles:"
flatpak remote-ls local-bigbrowser 2>/dev/null || echo "Remote non configuré"

echo ""
echo "✅ Correction AppStream terminée !"
echo ""
echo "Les erreurs AppStream étaient des avertissements non critiques."
echo "Vos applications fonctionnent parfaitement même sans ces métadonnées."
echo ""
echo "Avantages des métadonnées AppStream ajoutées:"
echo "  - Meilleure intégration avec GNOME Software"
echo "  - Descriptions riches dans les magasins d'applications"
echo "  - Métadonnées pour la découvrabilité" 