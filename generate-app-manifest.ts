#!/usr/bin/env -S deno run -A

interface AppMetadata {
  appId: string;
  appName: string;
  displayName: string;
  description: string;
  url: string;
  categories: string;
  keywords: string;
}

function parseArgs(args: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const val = args[i + 1] && !args[i + 1].startsWith("--") ? args[++i] : "true";
      out[key] = val;
    }
  }
  return out;
}

function joinPaths(...parts: string[]): string {
  return parts.join("/").replace(/\/+/g, "/");
}

async function main() {
  const args = parseArgs(Deno.args);
  const appDir = args["app-dir"] ? args["app-dir"] : ".";

  const scriptDir = new URL(".", import.meta.url).pathname;
  const templatePath = args["template"]
    ? args["template"]
    : joinPaths(scriptDir, "app-manifest-template.yml");

  const appDirAbs = appDir.startsWith("/") ? appDir : joinPaths(Deno.cwd(), appDir);
  const metadataPath = joinPaths(appDirAbs, "metadata.json");
  const outputPath = joinPaths(appDirAbs, "manifest.yml");

  try {
    const [template, metadataRaw] = await Promise.all([
      Deno.readTextFile(templatePath),
      Deno.readTextFile(metadataPath),
    ]);

    const meta: AppMetadata = JSON.parse(metadataRaw);

    const requiredFields: (keyof AppMetadata)[] = [
      "appId",
      "appName",
      "displayName",
      "description",
      "url",
      "categories",
      "keywords",
    ];

    for (const field of requiredFields) {
      if (!meta[field] || (typeof meta[field] === "string" && (meta[field] as string).trim() === "")) {
        throw new Error(`Champ manquant ou vide dans metadata.json: ${field}`);
      }
    }

    let rendered = template;
    const replacements: Record<string, string> = {
      "{{app_id}}": meta.appId,
      "{{app_name}}": meta.appName,
      "{{display_name}}": meta.displayName,
      "{{description}}": meta.description,
      "{{url}}": meta.url,
      "{{categories}}": meta.categories,
      "{{keywords}}": meta.keywords,
    };

    for (const [placeholder, value] of Object.entries(replacements)) {
      rendered = rendered.split(placeholder).join(value);
    }

    await Deno.writeTextFile(outputPath, rendered);

    console.log(`✅ manifest.yml généré: ${outputPath}`);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("❌ Échec de la génération du manifest:", message);
    Deno.exit(1);
  }
}

if (import.meta.main) {
  main();
} 