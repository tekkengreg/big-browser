#!/usr/bin/env -S deno run -A

// Scaffolder Deno pour générer un dossier apps/<app>/ par entrée dans flatpak_apps.json
// Génère: metadata.json, manifest.yml, icon.png (symlink), build.sh, install.sh

interface AppData {
  appName?: string;
  displayName?: string;
  description?: string;
  url?: string;
  categories?: string;
  keywords?: string;
}

const repoRoot = Deno.cwd();
const APPS_DIR = `${repoRoot}/packages/apps`;
const ICONS_DIR = `${repoRoot}/icons`;
const FLATPAK_APPS_FILE = `${repoRoot}/flatpak_apps.json`;

async function pathExists(path: string): Promise<boolean> {
  try {
    await Deno.stat(path);
    return true;
  } catch (_) {
    return false;
  }
}

async function ensureDir(path: string): Promise<void> {
  await Deno.mkdir(path, { recursive: true }).catch(() => {});
}

async function writeFile(path: string, content: string): Promise<void> {
  await ensureDir(path.substring(0, path.lastIndexOf('/')));
  await Deno.writeTextFile(path, content);
}

async function makeExecutable(path: string): Promise<void> {
  try {
    await Deno.chmod(path, 0o755);
  } catch (_) {
    // ignore on systems without chmod support
  }
}

function manifestContent(appName: string, app: AppData): string {
  return `app-id: com.tekkengreg.bigbrowser.${appName}
runtime: org.gnome.Platform
runtime-version: '48'
sdk: org.gnome.Sdk//48
command: ${appName}

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
  - --env=WEBKIT_DISABLE_COMPOSITING_MODE=1
  - --env=WEBKIT_DISABLE_DMABUF_RENDERER=1
  - --env=WEBKIT_FORCE_SANDBOX=0
  - --env=XDG_CURRENT_DESKTOP=GNOME

modules:
  - name: ${appName}
    buildsystem: simple
    build-commands:
      - echo "Installing ${app.displayName ?? appName}"
      - mkdir -p /app/bin /app/share/applications /app/share/icons/hicolor/128x128/apps /app/share/metainfo
      - install -Dm755 tauri-runtime /app/bin/tauri-runtime
      - install -Dm644 com.tekkengreg.bigbrowser.${appName}.png /app/share/icons/hicolor/128x128/apps/com.tekkengreg.bigbrowser.${appName}.png
      - |
        cat > /app/bin/${appName} << 'EOF'
        #!/bin/bash
        exec /app/bin/tauri-runtime "${app.url ?? ''}"
        EOF
      - chmod +x /app/bin/${appName}
      - |
        cat > /app/share/applications/com.tekkengreg.bigbrowser.${appName}.desktop << 'EOF'
        [Desktop Entry]
        Name=${app.displayName ?? appName}
        Comment=${app.description ?? ''}
        Exec=${appName}
        Icon=com.tekkengreg.bigbrowser.${appName}
        Terminal=false
        Type=Application
        StartupWMClass=${app.displayName ?? appName}
        Categories=${app.categories ?? ''}
        Keywords=${app.keywords ?? ''}
        StartupNotify=true
        MimeType=text/html;text/xml;application/xhtml+xml;application/xml;application/rss+xml;application/rdf+xml;image/gif;image/jpeg;image/png;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/chrome;video/webm;application/x-xpinstall;
        EOF
      - |
        cat > /app/share/metainfo/com.tekkengreg.bigbrowser.${appName}.metainfo.xml << 'EOF'
        <?xml version="1.0" encoding="UTF-8"?>
        <component type="desktop-application">
          <id>com.tekkengreg.bigbrowser.${appName}</id>
          <metadata_license>CC0-1.0</metadata_license>
          <project_license>MIT</project_license>
          <name>${app.displayName ?? appName}</name>
          <summary>${app.description ?? ''}</summary>
          <description>
            <p>${app.description ?? ''} powered by BigBrowser Runtime (Tauri).</p>
            <p>BigBrowser Runtime is a modern web browser runtime application built with Tauri and Rust.</p>
          </description>
          <categories>
            <category>Network</category>
            <category>WebBrowser</category>
          </categories>
          <url type="homepage">${app.url ?? ''}</url>
          <launchable type="desktop-id">com.tekkengreg.bigbrowser.${appName}.desktop</launchable>
          <provides>
            <binary>${appName}</binary>
          </provides>
        </component>
        EOF
    sources:
      - type: file
        path: ../../../build-dir-tauri-runtime/files/bin/tauri-runtime
        dest-filename: tauri-runtime
      - type: file
        path: ./icon.png
        dest-filename: com.tekkengreg.bigbrowser.${appName}.png`;
}

function buildShContent(appName: string): string {
  return `#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_ID="com.tekkengreg.bigbrowser.${appName}"
BUILD_DIR="../../build-dir-${appName}"

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
`;
}

function installShContent(appName: string): string {
  return `#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_ID="com.tekkengreg.bigbrowser.${appName}"
BUILD_DIR="../../build-dir-${appName}"

echo "=== Install $APP_ID (user) ==="
flatpak-builder --user --install --force-clean "$BUILD_DIR" ./manifest.yml
`;
}

function denoJsonContent(appName: string): string {
  return JSON.stringify({
    tasks: {
      "flatpak:build": `flatpak-builder --force-clean ../../build-dir-${appName} ./manifest.yml`,
    },
  }, null, 2) + "\n";
}

async function symlinkOrCopy(src: string, dest: string): Promise<void> {
  try {
    try {
      // Remove existing file/symlink if present
      await Deno.remove(dest);
    } catch (_) {
      // ignore
    }
    await Deno.copyFile(src, dest);
  } catch (_) {
  }
}

async function scaffoldOne(appName: string, app: AppData): Promise<boolean> {
  const iconSrc = `${ICONS_DIR}/${appName}.png`;
  if (!(await pathExists(iconSrc))) {
    console.log(`⚠️  IGNORÉ: ${appName} (icône manquante: ${iconSrc})`);
    return false;
  }

  const runtimeBin = `${repoRoot}/build-dir-tauri-runtime/files/bin/tauri-runtime`;
  if (!(await pathExists(runtimeBin))) {
    console.log(`⚠️  ${appName}: runtime manquant (${runtimeBin}). Exécutez './build-tauri-runtime.sh' puis relancez le scaffolding.`);
  }

  const appDir = `${APPS_DIR}/${appName}`;
  await ensureDir(appDir);

  // metadata.json
  const metadata = {
    appId: `com.tekkengreg.bigbrowser.${appName}`,
    appName: app.appName ?? appName,
    displayName: app.displayName ?? appName,
    description: app.description ?? "",
    url: app.url ?? "",
    categories: app.categories ?? "",
    keywords: app.keywords ?? "",
  };
  await writeFile(`${appDir}/metadata.json`, JSON.stringify(metadata, null, 2) + "\n");

  // manifest.yml
  await writeFile(`${appDir}/manifest.yml`, manifestContent(appName, app) + "\n");

  // icon symlink (apps/<app>/icon.png -> ../../icons/<app>.png)
  await symlinkOrCopy(`../../icons/${appName}.png`, `${appDir}/icon.png`);

  // build.sh & install.sh
  await writeFile(`${appDir}/build.sh`, buildShContent(appName));
  await makeExecutable(`${appDir}/build.sh`);

  await writeFile(`${appDir}/install.sh`, installShContent(appName));
  await makeExecutable(`${appDir}/install.sh`);

  // per-app deno.json with flatpak build task
  await writeFile(`${appDir}/deno.json`, denoJsonContent(appName));

  console.log(`✅ Scaffolé: apps/${appName} in ${appDir}`);
  return true;
}

async function main() {
  console.log("=== Scaffolding des apps depuis flatpak_apps.json ===");
  const appsText = await Deno.readTextFile(FLATPAK_APPS_FILE);
  const apps: Record<string, AppData> = JSON.parse(appsText);

  let created = 0;
  let skipped = 0;

  for (const [appName, appData] of Object.entries(apps)) {
    if (await scaffoldOne(appName, appData)) created++; else skipped++;
  }

  console.log("\n=== Résultat ===");
  console.log(`📁 Dossiers créés: ${created}`);
  console.log(`⚠️  Ignorés (icône manquante): ${skipped}`);
}

if (import.meta.main) {
  await main();
} 