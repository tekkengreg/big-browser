#!/bin/bash

set -e

echo "=== Script de diagnostic BigBrowser Runtime (Tauri) ==="

# Fonctions de diagnostic
check_flatpak_installation() {
    echo "🔍 Vérification de l'installation Flatpak..."
    if flatpak list --app | grep -q "com.tekkengreg.bigbrowser.runtime"; then
        echo "✅ Application installée"
        flatpak list --app | grep "com.tekkengreg.bigbrowser.runtime"
    else
        echo "❌ Application non trouvée"
        echo "💡 Exécutez: ./build-tauri-runtime.sh"
        exit 1
    fi
}

check_environment() {
    echo "🔍 Vérification de l'environnement..."
    echo "Session actuelle: $XDG_SESSION_TYPE"
    echo "Desktop: $XDG_CURRENT_DESKTOP"
    
    if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        echo "⚠️  Session Wayland détectée - des erreurs peuvent survenir"
        echo "💡 L'application force X11 pour éviter les problèmes"
    fi
}

test_basic_launch() {
    echo "🚀 Test de lancement basique..."
    
    # Test avec timeout pour éviter que ça reste bloqué
    timeout 10s flatpak run com.tekkengreg.bigbrowser.runtime https://httpbin.org/get 2>&1 | \
    head -20 | \
    while IFS= read -r line; do
        case "$line" in
            *"Error 71"*|*"Erreur de protocole"*)
                echo "❌ Erreur Wayland détectée: $line"
                ;;
            *"WebKit encountered an internal error"*)
                echo "❌ Erreur WebKit détectée: $line"
                ;;
            *"Failed to create"*)
                echo "❌ Erreur de création: $line"
                ;;
            *)
                echo "ℹ️  $line"
                ;;
        esac
    done || echo "✅ Application lancée (timeout normal après 10s)"
}

suggest_fixes() {
    echo ""
    echo "🛠️  Solutions aux problèmes courants:"
    echo ""
    echo "1. Erreurs Wayland:"
    echo "   - Forcez X11: export GDK_BACKEND=x11"
    echo "   - Ou utilisez: flatpak run --env=GDK_BACKEND=x11 com.tekkengreg.bigbrowser.runtime"
    echo ""
    echo "2. Erreurs WebKit:"
    echo "   - Désactivez la sandbox: --env=WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1"
    echo "   - Désactivez le compositing: --env=WEBKIT_DISABLE_COMPOSITING_MODE=1"
    echo ""
    echo "3. Problèmes de permissions:"
    echo "   - Vérifiez les permissions: flatpak info --show-permissions com.tekkengreg.bigbrowser.runtime"
    echo "   - Accordez plus d'accès: flatpak override --user --socket=wayland com.tekkengreg.bigbrowser.runtime"
    echo ""
    echo "4. Reconstruction complète:"
    echo "   - Nettoyez le cache: rm -rf .flatpak-builder/"
    echo "   - Reconstruisez: ./build-tauri-runtime.sh"
}

# Test avec différentes URLs
test_urls() {
    echo "🌐 Test avec différentes URLs..."
    
    local urls=(
        "https://httpbin.org/get"
        "https://www.wikipedia.org"
        "https://www.google.com"
    )
    
    for url in "${urls[@]}"; do
        echo "Testing: $url"
        timeout 5s flatpak run com.tekkengreg.bigbrowser.runtime "$url" >/dev/null 2>&1 && \
            echo "✅ $url - OK" || echo "❌ $url - Erreur"
    done
}

# Exécution du diagnostic
main() {
    check_flatpak_installation
    echo ""
    check_environment
    echo ""
    test_basic_launch
    echo ""
    test_urls
    echo ""
    suggest_fixes
}

# Options en ligne de commande
case "${1:-}" in
    --check)
        check_flatpak_installation
        ;;
    --env)
        check_environment
        ;;
    --test)
        test_basic_launch
        ;;
    --urls)
        test_urls
        ;;
    --help)
        echo "Usage: $0 [--check|--env|--test|--urls|--help]"
        echo "  --check : Vérifier l'installation"
        echo "  --env   : Vérifier l'environnement"
        echo "  --test  : Test de lancement"
        echo "  --urls  : Test avec URLs"
        echo "  --help  : Afficher cette aide"
        ;;
    *)
        main
        ;;
esac 