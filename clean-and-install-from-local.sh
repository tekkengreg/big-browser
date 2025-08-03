#!/bin/bash

# Script pour nettoyer les installations existantes et installer depuis le repository local

set -e

REPO_DIR="local-repo"
REMOTE_NAME="local-bigbrowser"

echo "=== Nettoyage et installation depuis le repository local ==="

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

# Lister les applications BigBrowser installées
echo ""
echo "🧹 Nettoyage des installations existantes..."
existing_apps=$(flatpak list --app | grep "com.tekkengreg.bigbrowser" | awk '{print $1}' || true)

if [ -n "$existing_apps" ]; then
    echo "📋 Applications à désinstaller:"
    echo "$existing_apps" | while read -r app_id; do
        echo "  - $app_id"
    done
    
    echo ""
    echo "🗑️  Désinstallation en cours..."
    echo "$existing_apps" | while read -r app_id; do
        if [ -n "$app_id" ]; then
            echo "🗑️  Désinstallation de $app_id..."
            flatpak uninstall --user -y "$app_id" > /dev/null 2>&1 || true
        fi
    done
    echo "✅ Nettoyage terminé"
else
    echo "📭 Aucune application BigBrowser installée"
fi

# Lister les applications disponibles dans le repository local
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
echo "💾 Installation des applications depuis le repository local..."

installed_count=0
failed_count=0

# Installer chaque application depuis le repository local
echo "$available_apps" | while IFS=$'\t' read -r name app_id branch; do
    if [ -n "$app_id" ]; then
        echo "📦 Installation de $name ($app_id)..."
        
        if flatpak install --user -y "$REMOTE_NAME" "$app_id" > /dev/null 2>&1; then
            echo "✅ $name installé avec succès"
            installed_count=$((installed_count + 1))
        else
            echo "❌ Échec de l'installation de $name"
            failed_count=$((failed_count + 1))
        fi
    fi
done

echo ""
echo "=== Vérification finale ==="
final_count=$(flatpak list --app | grep "com.tekkengreg.bigbrowser" | wc -l)
echo "📊 Applications BigBrowser installées: $final_count"

if [ $final_count -gt 0 ]; then
    echo ""
    echo "🎉 Applications installées depuis le repository local !"
    echo ""
    echo "📋 Applications disponibles:"
    flatpak list --app | grep "com.tekkengreg.bigbrowser" | while read -r app_id name branch version arch origin; do
        echo "  - $name ($app_id) depuis $origin"
    done
    echo ""
    echo "🎯 Utilisation:"
    echo "  flatpak run com.tekkengreg.bigbrowser.google"
    echo "  flatpak run com.tekkengreg.bigbrowser.youtube"
    echo "  flatpak run com.tekkengreg.bigbrowser.github"
    echo ""
    echo "🔧 Gestion:"
    echo "  flatpak list --app | grep bigbrowser    # Lister les apps"
    echo "  flatpak update                          # Mettre à jour"
    echo "  flatpak remote-ls local-bigbrowser      # Apps disponibles"
else
    echo "⚠️  Aucune application installée"
fi 