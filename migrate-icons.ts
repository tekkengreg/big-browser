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

async function symlinkOrCopy(src: string, dest: string): Promise<void> {
  console.log(`🔍 Copie de ${src} vers ${dest}`);
  try {
    try {
      // Remove existing file/symlink if present
      await Deno.remove(dest);
    } catch (_) {
      // ignore
    }
    await Deno.copyFile(src, dest);
  } catch (_) {
    console.log(`❌ Erreur lors de la copie de ${src} vers ${dest}`);
  }
}

async function main() {
  console.log("=== Migrating icons to apps ===");
  const appsText = await Deno.readTextFile(FLATPAK_APPS_FILE);
  const apps: Record<string, AppData> = JSON.parse(appsText);

  let created = 0;
  for (const [appName, ] of Object.entries(apps)) {
    await symlinkOrCopy(`${ICONS_DIR}/${appName}.png`, `${APPS_DIR}/${appName}/icon.png`)
    created++;
  }

  console.log(`✅ Migré: ${created} icons`);
}

if (import.meta.main) {
  await main();
} 