#!/bin/bash

# Menu interactif pour BigBrowser Flatpak

clear
echo "=============================================="
echo "🚀 MENU BIGBROWSER FLATPAK"
echo "=============================================="
echo ""

while true; do
    echo "📋 ACTIONS DISPONIBLES:"
    echo ""
    echo "  🔧 CONSTRUCTION ET GESTION"
    echo "  1) Workflow complet (recommandé)"
    echo "  2) Construire toutes les applications"
    echo "  3) Configurer le repository local"
    echo "  4) Installer depuis le repository local"
    echo "  5) Nettoyer et réinstaller"
    echo ""
    echo "  📦 EXPORT ET DISTRIBUTION"
    echo "  6) Exporter vers fichiers .flatpak"
    echo "  7) Générer les manifestes seulement"
    echo ""
    echo "  📊 INFORMATION ET DIAGNOSTIC"
    echo "  8) Statut du système"
    echo "  9) Lister les applications installées"
    echo "  10) Tester une application"
    echo ""
    echo "  📚 DOCUMENTATION"
    echo "  11) Voir la documentation complète"
    echo "  12) Voir la documentation repository local"
    echo ""
    echo "  0) Quitter"
    echo ""
    
    read -p "Choisissez une option (0-12): " choice
    echo ""
    
    case $choice in
        1)
            echo "🚀 Lancement du workflow complet..."
            ./workflow-complete.sh
            ;;
        2)
            echo "📦 Construction de toutes les applications..."
            ./build-all-apps.sh
            ;;
        3)
            echo "🗂️ Configuration du repository local..."
            ./setup-local-repo.sh
            ;;
        4)
            echo "💾 Installation depuis le repository local..."
            ./install-from-local-repo.sh
            ;;
        5)
            echo "🧹 Nettoyage et réinstallation..."
            ./clean-and-install-from-local.sh
            ;;
        6)
            echo "📤 Export vers fichiers .flatpak..."
            ./export-all-apps.sh
            ;;
        7)
            echo "📝 Génération des manifestes..."
            python3 generate-app-manifests.py
            ;;
        8)
            echo "📊 STATUT DU SYSTÈME BIGBROWSER"
            echo "=============================================="
            echo ""
            if [ -f "bigbrowser" ]; then
                echo "✅ Exécutable BigBrowser: $(du -h bigbrowser | cut -f1)"
            else
                echo "❌ Exécutable BigBrowser: manquant"
            fi
            
            if [ -d "local-repo" ]; then
                echo "✅ Repository local: $(du -sh local-repo | cut -f1)"
            else
                echo "❌ Repository local: non configuré"
            fi
            
            apps_repo=$(flatpak remote-ls local-bigbrowser 2>/dev/null | wc -l || echo "0")
            echo "📦 Applications dans le repository: $apps_repo"
            
            apps_installed=$(flatpak list --app | grep local-bigbrowser | wc -l || echo "0")
            echo "💾 Applications installées: $apps_installed"
            
            if [ -d "dist" ]; then
                flatpaks=$(ls dist/*.flatpak 2>/dev/null | wc -l || echo "0")
                echo "📁 Fichiers .flatpak: $flatpaks"
            else
                echo "📁 Fichiers .flatpak: 0"
            fi
            ;;
        9)
            echo "📋 APPLICATIONS INSTALLÉES"
            echo "=============================================="
            flatpak list --app | grep bigbrowser || echo "Aucune application BigBrowser installée"
            ;;
        10)
            echo "🧪 TESTER UNE APPLICATION"
            echo "=============================================="
            echo "Applications disponibles:"
            flatpak list --app | grep bigbrowser | awk '{print "  - " $2 " (" $1 ")"}'
            echo ""
            read -p "Entrez le nom de l'application (ex: github, youtube): " app_name
            if [ -n "$app_name" ]; then
                echo "🚀 Lancement de $app_name..."
                timeout 10s flatpak run "com.tekkengreg.bigbrowser.$app_name" || echo "Application fermée ou erreur"
            fi
            ;;
        11)
            echo "📚 DOCUMENTATION COMPLÈTE"
            echo "=============================================="
            if [ -f "README-APPS.md" ]; then
                echo "📖 Ouverture de README-APPS.md..."
                less README-APPS.md
            else
                echo "❌ Documentation non trouvée"
            fi
            ;;
        12)
            echo "📚 DOCUMENTATION REPOSITORY LOCAL"
            echo "=============================================="
            if [ -f "README-LOCAL-REPO.md" ]; then
                echo "📖 Ouverture de README-LOCAL-REPO.md..."
                less README-LOCAL-REPO.md
            else
                echo "❌ Documentation repository local non trouvée"
            fi
            ;;
        0)
            echo "👋 Au revoir !"
            exit 0
            ;;
        *)
            echo "❌ Option invalide. Veuillez choisir entre 0 et 12."
            ;;
    esac
    
    echo ""
    echo "=============================================="
    read -p "Appuyez sur Entrée pour continuer..."
    clear
    echo "=============================================="
    echo "🚀 MENU BIGBROWSER FLATPAK"
    echo "=============================================="
    echo ""
done 