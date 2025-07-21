#!/bin/bash

echo "📊 MESURE DES TAILLES DES APPLICATIONS FLATPAK"
echo "==============================================="
echo ""

echo "🏗️  APPLICATION DE BASE (com.tekkengreg.bigbrowser.Base):"
if [ -d ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.Base ]; then
    base_size=$(du -sh ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.Base | cut -f1)
    echo "   ✅ Installée - Taille: $base_size"
else
    echo "   ❌ Non installée"
fi

if [ -d build-dir-base ]; then
    build_size=$(du -sh build-dir-base | cut -f1)
    echo "   📁 Répertoire de build: $build_size"
fi
echo ""

echo "📱 APPLICATIONS LÉGÈRES:"
for app in google notion sketchup; do
    app_id="com.tekkengreg.bigbrowser.$app"
    echo "   🔹 $app:"
    
    if [ -d ~/.local/share/flatpak/app/$app_id ]; then
        install_size=$(du -sh ~/.local/share/flatpak/app/$app_id | cut -f1)
        echo "      ✅ Installée - Taille: $install_size"
    else
        echo "      ❌ Non installée"
    fi
    
    if [ -d build-dir-$app ]; then
        build_size=$(du -sh build-dir-$app | cut -f1)
        echo "      📁 Build: $build_size"
    fi
done
echo ""

echo "📊 COMPARAISON AVEC L'ANCIENNE ARCHITECTURE:"
echo "   Avant (par app): ~250MB (Node.js + Electron + Code)"
echo "   Après:"
echo "     • Base partagée: 906MB (une seule fois)"
echo "     • Apps légères: ~15MB chacune (overhead Flatpak)"
echo "     • Gain net: Massif à partir de la 2ème application"
echo ""

echo "💾 ESPACE DISQUE TOTAL UTILISÉ:"
if [ -d ~/.local/share/flatpak/app ]; then
    total_size=$(du -sh ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.* | awk '{sum+=$1} END {print sum}' 2>/dev/null || echo "Calcul impossible")
    echo "   Toutes les apps BigBrowser: $(du -ch ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.* | tail -1 | cut -f1)"
else
    echo "   Aucune application installée"
fi
echo ""

echo "🔍 COMMANDES UTILES POUR MESURER LES TAILLES:"
echo "   # Taille d'une app spécifique:"
echo "   du -sh ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.google"
echo ""
echo "   # Toutes les apps BigBrowser:"
echo "   du -sh ~/.local/share/flatpak/app/com.tekkengreg.bigbrowser.*"
echo ""
echo "   # Taille des builds:"
echo "   du -sh build-dir-*"
echo ""
echo "   # Infos Flatpak:"
echo "   flatpak info com.tekkengreg.bigbrowser.Base" 