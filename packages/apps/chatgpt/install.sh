#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_ID="com.tekkengreg.bigbrowser.chatgpt"
BUILD_DIR="../../build-dir-chatgpt"

echo "=== Install $APP_ID (user) ==="
flatpak-builder --user --install --force-clean "$BUILD_DIR" ./manifest.yml
