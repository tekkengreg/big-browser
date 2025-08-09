#!/usr/bin/env -S deno run -A

/**
 * Migration des manifests sous packages/apps pour utiliser le runtime Tauri.
 * - Remplace l'installation de bigbrowser par tauri-runtime
 * - Modifie l'exec wrapper pour pointer vers /app/bin/tauri-runtime "<URL>"
 * - Remplace la source ../../bigbrowser par ../../../build-dir-tauri-runtime/files/bin/tauri-runtime + dest-filename
 * - Ajuste la description/metainfo pour mentionner le runtime Tauri
 * - Corrige l'installation de l'icône: utiliser le fichier staged 'com.tekkengreg.bigbrowser.<app>.png' instead of './icon.png'
 */

const BASE = `${Deno.cwd()}/packages/apps`;

for await (const entry of Deno.readDir(BASE)) {
  if (!entry.isDirectory) continue;
  const shortName = entry.name;
  const appId = `com.tekkengreg.bigbrowser.${shortName}`;
  const manifestPath = `${BASE}/${entry.name}/manifest.yml`;
  try {
    let content = await Deno.readTextFile(manifestPath);

    // install bigbrowser -> tauri-runtime
    content = content.replace(
      /install -Dm755\s+\.\.\/\.\.\/bigbrowser\s+\/app\/bin\/bigbrowser/g,
      'install -Dm755 tauri-runtime /app/bin/tauri-runtime',
    );
    content = content.replace(
      /install -Dm755\s+bigbrowser\s+\/app\/bin\/bigbrowser/g,
      'install -Dm755 tauri-runtime /app/bin/tauri-runtime',
    );

    // wrapper exec
    content = content.replace(
      /exec \/app\/bin\/bigbrowser\s+"/g,
      'exec /app/bin/tauri-runtime "',
    );

    // sources path to runtime binary
    content = content.replace(
      /(\n\s{6}- type: file\n\s{8}path:\s*\.\.\/\.\.\/bigbrowser)/,
      '\n      - type: file\n        path: ../../../build-dir-tauri-runtime/files/bin/tauri-runtime\n        dest-filename: tauri-runtime',
    );
    content = content.replace(
      /(\n\s{8}path:\s*\.\.\/bigbrowser)/,
      '\n        path: ../../../build-dir-tauri-runtime/files/bin/tauri-runtime\n        dest-filename: tauri-runtime',
    );

    // icon install: use staged dest-filename instead of ./icon.png
    const iconFile = `${appId}.png`;
    content = content.replace(
      /install -Dm644\s+\.\/icon\.png\s+\/app\/share\/icons\/hicolor\/128x128\/apps\/com\.tekkengreg\.bigbrowser\.[a-z0-9\-]+\.png/g,
      `install -Dm644 ${iconFile} /app/share/icons/hicolor/128x128/apps/${iconFile}`,
    );

    // metainfo description lines
    content = content.replace(
      /powered by BigBrowser\./g,
      'powered by BigBrowser Runtime (Tauri).',
    );
    content = content.replace(
      /BigBrowser is a simple web browser built with Deno that provides native desktop applications for web services\./g,
      'BigBrowser Runtime is a modern web browser runtime application built with Tauri and Rust.',
    );

    // Optional: add env flags if not present
    if (!/WEBKIT_DISABLE_COMPOSITING_MODE/.test(content)) {
      content = content.replace(
        /(\nfinish-args:[\s\S]*?WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1)/,
        '$1\n  - --env=WEBKIT_DISABLE_COMPOSITING_MODE=1\n  - --env=WEBKIT_DISABLE_DMABUF_RENDERER=1\n  - --env=WEBKIT_FORCE_SANDBOX=0\n  - --env=XDG_CURRENT_DESKTOP=GNOME',
      );
    }

    await Deno.writeTextFile(manifestPath, content);
    console.log(`✅ Migré: packages/apps/${entry.name}/manifest.yml`);
  } catch (_) {
    // skip if manifest missing
  }
} 