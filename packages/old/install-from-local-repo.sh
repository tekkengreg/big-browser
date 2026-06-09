#!/bin/bash

# Script pour installer toutes les applications depuis le repository local

set -e

REPO_DIR="local-repo"
REMOTE_NAME="local-bigbrowser"

echo "=== Installation des applications depuis le repository local ==="

# Vérifier que le repository local existe
if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Erreur: Repository local '$REPO_DIR' n'existe pas"
    echo "   Exécutez d'abord: ./setup-local-repo.sh"
    exit 1
fi

# Ajouter le remote s'il n'existe pas déjà
if ! flatpak remote-list --user | grep -q "$REMOTE_NAME"; then
    echo "📡 Ajout du remote '$REMOTE_NAME'..."
    flatpak remote-add --user --no-gpg-verify "$REMOTE_NAME" "file://$(pwd)/$REPO_DIR"
    echo "✅ Remote ajouté"
else
    echo "📡 Remote '$REMOTE_NAME' déjà configuré"
fi

# Mettre à jour le remote
echo "🔄 Mise à jour du remote..."
flatpak update --appstream "$REMOTE_NAME" > /dev/null 2>&1 || true

# Lister les applications disponibles
echo ""
echo "📋 Applications disponibles dans le repository local:"
available_apps=$(flatpak remote-ls "$REMOTE_NAME" --app 2>/dev/null | grep "com.tekkengreg.bigbrowser" || true)

if [ -z "$available_apps" ]; then
    echo "⚠️  Aucune application trouvée dans le repository local"
    echo "   Assurez-vous d'avoir exécuté ./setup-local-repo.sh après la construction"
    exit 1
fi

echo "$available_apps"

echo ""
echo "💾 Installation des applications..."

installed_count=0
failed_count=0

# Installer chaque application depuis le repository local
while IFS= read -r line; do
    if [ -n "$line" ]; then
        app_id=$(echo "$line" | awk '{print $1}')
        app_name=$(echo "$line" | awk '{print $2}')
        
        echo "📦 Installation de $app_name ($app_id)..."
        
        if flatpak install --user -y "$REMOTE_NAME" "$app_id" > /dev/null 2>&1; then
            echo "✅ $app_name installé avec succès"
            installed_count=$((installed_count + 1))
        else
            echo "❌ Échec de l'installation de $app_name"
            failed_count=$((failed_count + 1))
        fi
    fi
done <<< "$available_apps"

echo ""
echo "=== Résumé de l'installation ==="
echo "✅ Applications installées: $installed_count"
echo "❌ Échecs: $failed_count"
echo "📦 Total: $((installed_count + failed_count))"

if [ $installed_count -gt 0 ]; then
    echo ""
    echo "🎉 Applications installées depuis le repository local !"
    echo ""
    echo "Vous pouvez maintenant utiliser vos applications:"
    echo "  flatpak run com.tekkengreg.bigbrowser.google"
    echo "  flatpak run com.tekkengreg.bigbrowser.youtube"
    echo "  flatpak run com.tekkengreg.bigbrowser.github"
    echo "  etc..."
    echo ""
    echo "Pour voir toutes les applications installées:"
    echo "  flatpak list --app | grep bigbrowser"
    echo ""
    echo "Pour mettre à jour les applications:"
    echo "  flatpak update"
fi 