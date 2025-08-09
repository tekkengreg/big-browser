#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_ID="com.tekkengreg.bigbrowser.chatgpt"
BUILD_DIR="../../build-dir-chatgpt"

if [ ! -f ../../build-dir-tauri-runtime/files/bin/tauri-runtime ]; then
  echo "Erreur: le binaire du runtime est manquant ('../../build-dir-tauri-runtime/files/bin/tauri-runtime'). Construisez d'abord le runtime."
  echo "Indice: ./build-tauri-runtime.sh"
  exit 1
fi

if [ ! -f ./manifest.yml ]; then
  echo "Erreur: manifest.yml introuvable."
  exit 1
fi

echo "=== Build $APP_ID ==="
flatpak-builder --force-clean "$BUILD_DIR" ./manifest.yml
