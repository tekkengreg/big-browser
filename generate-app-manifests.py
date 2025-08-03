#!/usr/bin/env python3

import json
import os
from pathlib import Path

def load_apps():
    """Charge les applications depuis flatpak_apps.json"""
    with open('flatpak_apps.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_manifest(app_name, app_data):
    """Crée un manifeste Flatpak pour une application donnée"""
    
    # Template du manifeste
    manifest = f"""app-id: com.tekkengreg.bigbrowser.{app_name}
runtime: org.gnome.Platform
runtime-version: '48'
sdk: org.gnome.Sdk//48
command: {app_name}

finish-args:
  - --share=ipc
  - --socket=x11
  - --socket=wayland
  - --socket=fallback-x11
  - --share=network
  - --device=dri
  - --socket=pulseaudio
  - --socket=session-bus
  - --talk-name=org.freedesktop.Flatpak
  - --system-talk-name=org.freedesktop.NetworkManager
  - --talk-name=org.freedesktop.secrets
  - --talk-name=org.freedesktop.portal.*
  - --talk-name=org.a11y.Bus
  - --filesystem=xdg-download:rw
  - --filesystem=xdg-documents:rw
  - --filesystem=xdg-pictures:rw
  - --filesystem=xdg-videos:rw
  - --env=GTK_USE_PORTAL=1
  - --env=WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1

modules:
  - name: {app_name}
    buildsystem: simple
    build-commands:
      - echo "Installing {app_data['displayName']}"
      - mkdir -p /app/bin /app/share/applications /app/share/icons/hicolor/128x128/apps /app/share/metainfo
      - install -Dm755 bigbrowser /app/bin/bigbrowser
      - install -Dm644 com.tekkengreg.bigbrowser.{app_name}.png /app/share/icons/hicolor/128x128/apps/com.tekkengreg.bigbrowser.{app_name}.png
      - |
        cat > /app/bin/{app_name} << 'EOF'
        #!/bin/bash
        exec /app/bin/bigbrowser "{app_data['url']}"
        EOF
      - chmod +x /app/bin/{app_name}
      - |
        cat > /app/share/applications/com.tekkengreg.bigbrowser.{app_name}.desktop << 'EOF'
        [Desktop Entry]
        Name={app_data['displayName']}
        Comment={app_data['description']}
        Exec={app_name}
        Icon=com.tekkengreg.bigbrowser.{app_name}
        Terminal=false
        Type=Application
        StartupWMClass={app_data['displayName']}
        Categories={app_data['categories']}
        Keywords={app_data['keywords']}
        StartupNotify=true
        MimeType=text/html;text/xml;application/xhtml+xml;application/xml;application/rss+xml;application/rdf+xml;image/gif;image/jpeg;image/png;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/chrome;video/webm;application/x-xpinstall;
        EOF
      - |
        cat > /app/share/metainfo/com.tekkengreg.bigbrowser.{app_name}.metainfo.xml << 'EOF'
        <?xml version="1.0" encoding="UTF-8"?>
        <component type="desktop-application">
          <id>com.tekkengreg.bigbrowser.{app_name}</id>
          <metadata_license>CC0-1.0</metadata_license>
          <project_license>MIT</project_license>
          <name>{app_data['displayName']}</name>
          <summary>{app_data['description']}</summary>
          <description>
            <p>{app_data['description']} powered by BigBrowser.</p>
            <p>BigBrowser is a simple web browser built with Deno that provides native desktop applications for web services.</p>
          </description>
          <categories>
            <category>Network</category>
            <category>WebBrowser</category>
          </categories>
          <url type="homepage">{app_data['url']}</url>
          <launchable type="desktop-id">com.tekkengreg.bigbrowser.{app_name}.desktop</launchable>
          <provides>
            <binary>{app_name}</binary>
          </provides>
        </component>
        EOF
    sources:
      - type: file
        path: ../bigbrowser
      - type: file
        path: ../icons/{app_name}.png
        dest-filename: com.tekkengreg.bigbrowser.{app_name}.png"""
    
    return manifest

def main():
    """Fonction principale"""
    print("=== Génération des manifestes Flatpak ===")
    
    # Charger les applications
    apps = load_apps()
    
    # Créer le dossier manifests s'il n'existe pas
    manifests_dir = Path('manifests')
    manifests_dir.mkdir(exist_ok=True)
    
    generated_count = 0
    skipped_count = 0
    
    for app_name, app_data in apps.items():
        # Vérifier que l'icône existe
        icon_path = Path(f'icons/{app_name}.png')
        if not icon_path.exists():
            print(f"⚠️  IGNORÉ: {app_name} (icône manquante: {icon_path})")
            skipped_count += 1
            continue
        
        # Créer le manifeste
        manifest_content = create_manifest(app_name, app_data)
        
        # Écrire le fichier manifeste
        manifest_path = manifests_dir / f'com.tekkengreg.bigbrowser.{app_name}.yml'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(manifest_content)
        
        print(f"✅ Généré: {manifest_path}")
        generated_count += 1
    
    print(f"\n=== Résumé ===")
    print(f"📦 Manifestes générés: {generated_count}")
    print(f"⚠️  Applications ignorées: {skipped_count}")
    print(f"\nPour construire toutes les applications, utilisez:")
    print(f"./build-all-apps.sh")

if __name__ == "__main__":
    main() 