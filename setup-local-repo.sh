#!/bin/bash

# Script pour configurer et gérer le repository local BigBrowser

set -e

REPO_DIR="local-repo"

echo "=== Configuration du repository local BigBrowser ==="

# Créer le répertoire du repository s'il n'existe pas
if [ ! -d "$REPO_DIR" ]; then
    echo "📁 Création du repository local..."
    mkdir -p "$REPO_DIR"
    ostree init --mode=archive-z2 --repo="$REPO_DIR"
    echo "✅ Repository '$REPO_DIR' initialisé"
else
    echo "📁 Repository '$REPO_DIR' existe déjà"
fi

# Fonction pour exporter une application vers le repository
export_to_repo() {
    local app_name="$1"
    local build_dir="$2"
    
    echo "📦 Export de $app_name vers le repository local..."
    
    if [ ! -d "$build_dir" ]; then
        echo "⚠️  IGNORÉ: $app_name (répertoire de build manquant: $build_dir)"
        return 1
    fi
    
    # Exporter vers le repository local
    if flatpak build-export "$REPO_DIR" "$build_dir" > /dev/null 2>&1; then
        echo "✅ $app_name exporté vers le repository local"
        return 0
    else
        echo "❌ Échec de l'export de $app_name"
        return 1
    fi
}

# Exporter toutes les applications construites vers le repository
exported_count=0
failed_count=0

echo ""
echo "🚀 Export des applications vers le repository local..."

for manifest in manifests/com.tekkengreg.bigbrowser.*.yml; do
    # Extraire le nom de l'app du fichier manifeste
    app_name=$(basename "$manifest" .yml)
    
    # Ignorer le manifeste principal
    if [[ "$app_name" == "com.tekkengreg.bigbrowser" ]]; then
        continue
    fi
    
    # Nom du répertoire de build
    short_name="${app_name##*.}"
    build_dir="build-dir-$short_name"
    
    if export_to_repo "$app_name" "$build_dir"; then
        exported_count=$((exported_count + 1))
    else
        failed_count=$((failed_count + 1))
    fi
done

echo ""
echo "=== Résumé de l'export vers le repository ==="
echo "✅ Applications exportées: $exported_count"
echo "❌ Échecs: $failed_count"
echo "📦 Total: $((exported_count + failed_count))"

if [ $exported_count -gt 0 ]; then
    echo ""
    echo "🎉 Repository local configuré avec succès !"
    echo ""
    echo "Repository local: $(pwd)/$REPO_DIR"
    echo ""
    echo "Pour ajouter ce repository à Flatpak:"
    echo "  flatpak remote-add --user --no-gpg-verify local-bigbrowser file://$(pwd)/$REPO_DIR"
    echo ""
    echo "Pour installer les applications depuis le repository local:"
    echo "  ./install-from-local-repo.sh"
    echo ""
    echo "Pour lister les applications disponibles:"
    echo "  flatpak remote-ls local-bigbrowser"
fi 