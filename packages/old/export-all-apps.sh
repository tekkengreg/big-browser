#!/bin/bash

# Script pour exporter toutes les applications vers des fichiers .flatpak

set -e

echo "=== Export de toutes les applications BigBrowser ==="

# Créer le dossier de distribution s'il n'existe pas
mkdir -p dist

exported_count=0
failed_count=0

# Exporter chaque application construite
for manifest in packages/apps/*/manifest.yml; do
    app_dir=$(dirname "$manifest")
    short_name=$(basename "$app_dir")
    app_id="com.tekkengreg.bigbrowser.${short_name}"
    build_dir="build-dir-${short_name}"

    # Vérifier que le répertoire de build existe
    if [ ! -d "$build_dir" ]; then
        echo "⚠️  IGNORÉ: $app_id (répertoire de build manquant: $build_dir)"
        echo "   Construisez d'abord avec: ./build-all-apps.sh"
        failed_count=$((failed_count + 1))
        continue
    fi

    echo "📦 Export de $app_id..."

    output_file="dist/${short_name}.flatpak"

    temp_repo="temp-repo-${short_name}"
    mkdir -p "$temp_repo"

    if flatpak build-export "$temp_repo" "$build_dir" > /dev/null 2>&1; then
        if flatpak build-bundle "$temp_repo" "$output_file" "$app_id" > /dev/null 2>&1; then
            rm -rf "$temp_repo"
            size=$(du -h "$output_file" | cut -f1)
            echo "✅ $app_id exporté vers $output_file ($size)"
            exported_count=$((exported_count + 1))
        else
            echo "❌ Échec de la création du bundle pour $app_id"
            rm -rf "$temp_repo"
            failed_count=$((failed_count + 1))
        fi
    else
        echo "❌ Échec de l'export vers le repository pour $app_id"
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