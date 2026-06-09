#!/usr/bin/env -S deno run -A

/**
 * Migration des manifests existants pour utiliser le runtime Tauri.
 *
 * Modifications effectuées sur chaque manifest com.tekkengreg.bigbrowser.*.yml (hors runtime):
 * - Remplace l'installation du binaire "bigbrowser" par "tauri-runtime"
 * - Modifie le wrapper pour exécuter /app/bin/tauri-runtime "<URL>"
 * - Remplace la source ../bigbrowser par ../../../build-dir-tauri-runtime/files/bin/tauri-runtime + dest-filename
 * - Actualise la description metainfo pour mentionner BigBrowser Runtime (Tauri)
 */

const MANIFESTS_DIR = `${Deno.cwd()}/manifests`;

for await (const entry of Deno.readDir(MANIFESTS_DIR)) {
  console.log(`Processing ${entry.name}`);
  if (!entry.isFile || !entry.name.endsWith('.yml')) continue;
  if (entry.name === 'com.tekkengreg.bigbrowser.yml') continue;
  if (entry.name === 'com.tekkengreg.bigbrowser.runtime.yml') continue;

  const path = `${MANIFESTS_DIR}/${entry.name}`;
  let content = await Deno.readTextFile(path);

  // install line: bigbrowser -> tauri-runtime
  content = content.replace(
    /install -Dm755\s+bigbrowser\s+\/app\/bin\/bigbrowser/g,
    'install -Dm755 tauri-runtime /app/bin/tauri-runtime',
  );

  // wrapper exec: bigbrowser -> tauri-runtime
  content = content.replace(
    /exec \/app\/bin\/bigbrowser\s+"/g,
    'exec /app/bin/tauri-runtime "',
  );

  // source path to bigbrowser -> tauri-runtime with dest-filename
  // Replace the line with correct indentation and add dest-filename just below
  content = content.replace(
    /(\n\s{8}path:\s*\.\.\/bigbrowser)/,
    '\n        path: ../../../build-dir-tauri-runtime/files/bin/tauri-runtimeeeeee\n        dest-filename: tauri-runtime',
  );

  // metainfo description lines
  content = content.replace(
    /powered by BigBrowser\./g,
    'powered by BigBrowser Runtime (Tauriiii).',
  );
  content = content.replace(
    /BigBrowser is a simple web browser built with Deno that provides native desktop applications for web services\./g,
    'BigBrowser Runtime is a modern web browser runtime application built with Tauri and Rust.',
  );

  await Deno.writeTextFile(path, content);
  console.log(`✅ Migré: ${entry.name} to ${path}`);
} 