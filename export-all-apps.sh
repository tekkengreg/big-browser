#!/bin/bash

# Script pour exporter toutes les applications vers des fichiers .flatpak

set -e

echo "=== Export de toutes les applications BigBrowser ==="

# Créer le dossier de distribution s'il n'existe pas
mkdir -p dist

exported_count=0
failed_count=0

# Exporter chaque application construite
for manifest in manifests/com.tekkengreg.bigbrowser.*.yml; do
    # Extraire le nom de l'app du fichier manifeste
    app_name=$(basename "$manifest" .yml)
    
    # Ignorer le manifeste principal
    if [[ "$app_name" == "com.tekkengreg.bigbrowser" ]]; then
        continue
    fi
    
    # Nom de l'application courte
    short_name="${app_name##*.}"
    
    # Nom du répertoire de build
    build_dir="build-dir-$short_name"
    
    # Vérifier que le répertoire de build existe
    if [ ! -d "$build_dir" ]; then
        echo "⚠️  IGNORÉ: $app_name (répertoire de build manquant: $build_dir)"
        echo "   Construisez d'abord avec: ./build-all-apps.sh"
        failed_count=$((failed_count + 1))
        continue
    fi
    
    echo "📦 Export de $app_name..."
    
    # Nom du fichier de sortie
    output_file="dist/$short_name.flatpak"
    
    # Créer le répertoire repo temporaire pour cette app
    temp_repo="temp-repo-$short_name"
    mkdir -p "$temp_repo"
    
    # Exporter vers le repository
    if flatpak build-export "$temp_repo" "$build_dir" > /dev/null 2>&1; then
        # Créer le bundle .flatpak
        if flatpak build-bundle "$temp_repo" "$output_file" "$app_name" > /dev/null 2>&1; then
            # Nettoyer le repo temporaire
            rm -rf "$temp_repo"
            
            # Afficher la taille du fichier
            size=$(du -h "$output_file" | cut -f1)
            echo "✅ $app_name exporté vers $output_file ($size)"
            exported_count=$((exported_count + 1))
        else
            echo "❌ Échec de la création du bundle pour $app_name"
            rm -rf "$temp_repo"
            failed_count=$((failed_count + 1))
        fi
    else
        echo "❌ Échec de l'export vers le repository pour $app_name"
        rm -rf "$temp_repo"
        failed_count=$((failed_count + 1))
    fi
done

echo ""
echo "=== Résumé de l'export ==="
echo "✅ Applications exportées: $exported_count"
echo "❌ Échecs: $failed_count"
echo "📦 Total: $((exported_count + failed_count))"

if [ $exported_count -gt 0 ]; then
    echo ""
    echo "🎉 Applications exportées avec succès dans le dossier 'dist/' !"
    echo ""
    echo "Fichiers créés:"
    ls -lh dist/*.flatpak 2>/dev/null || echo "Aucun fichier .flatpak trouvé"
    echo ""
    echo "Pour installer un fichier .flatpak sur un autre système:"
    echo "  flatpak install --user dist/google.flatpak"
    echo "  flatpak install --user dist/youtube.flatpak"
    echo "  etc..."
fi 