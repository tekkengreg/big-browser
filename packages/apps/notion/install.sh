#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_ID="com.tekkengreg.bigbrowser.notion"
BUILD_DIR="../../build-dir-notion"

echo "=== Install $APP_ID (user) ==="
flatpak-builder --user --install --force-clean "$BUILD_DIR" ./manifest.yml
