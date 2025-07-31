#!/usr/bin/env node

const fs = require('fs');
const { exec } = require('child_process');
const path = require('path');
const https = require('https');
const http = require('http');

// Configuration des applications
const appConfigs = require('./flatpak_apps.json');

// Créer le dossier icons s'il n'existe pas
const iconsDir = './icons';
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

function downloadIcon(iconUrl, appName) {
  return new Promise((resolve) => {
    console.log(`📥 Téléchargement de l'icône pour ${appName}: ${iconUrl}`);

    // Déterminer l'extension basée sur l'URL
    let extension = '.png';
    const urlPath = new URL(iconUrl).pathname;
    if (urlPath) {
      const urlExt = path.extname(urlPath).toLowerCase();
      if (['.svg', '.png', '.jpg', '.jpeg', '.ico'].includes(urlExt)) {
        extension = urlExt;
      }
    }

    const iconPath = path.join(iconsDir, `${appName}${extension}`);
    const client = iconUrl.startsWith('https:') ? https : http;

    const request = client.get(iconUrl, (response) => {
      if (response.statusCode === 200) {
        const chunks = [];
        response.on('data', (chunk) => chunks.push(chunk));
        response.on('end', () => {
          const buffer = Buffer.concat(chunks);
          fs.writeFileSync(iconPath, buffer);
          console.log(`✅ Icône téléchargée: ${iconPath}`);
          resolve(iconPath);
        });
      } else if (response.statusCode === 301 || response.statusCode === 302) {
        // Follow redirect
        const redirectUrl = response.headers.location;
        console.log(`🔄 Redirection vers: ${redirectUrl}`);
        downloadIcon(redirectUrl, appName).then(resolve);
      } else {
        console.warn(`⚠️  HTTP ${response.statusCode} pour ${appName}`);
        tryFavicon(iconUrl, appName).then(resolve);
      }
    }).on('error', (error) => {
      console.warn(`⚠️  Erreur de téléchargement pour ${appName}: ${error.message}`);
      tryFavicon(iconUrl, appName).then(resolve);
    });

    // Timeout after 10 seconds
    request.setTimeout(10000, () => {
      request.destroy();
      console.warn(`⚠️  Timeout pour ${appName}`);
      tryFavicon(iconUrl, appName).then(resolve);
    });
  });
}

function tryFavicon(originalUrl, appName) {
  return new Promise((resolve) => {
    try {
      const url = new URL(originalUrl);
      const faviconUrl = `${url.protocol}//${url.hostname}/favicon.ico`;
      console.log(`🔄 Tentative avec favicon: ${faviconUrl}`);

      const iconPath = path.join(iconsDir, `${appName}.ico`);
      const client = faviconUrl.startsWith('https:') ? https : http;

      const request = client.get(faviconUrl, (response) => {
        if (response.statusCode === 200) {
          const chunks = [];
          response.on('data', (chunk) => chunks.push(chunk));
          response.on('end', () => {
            const buffer = Buffer.concat(chunks);
            if (buffer.length > 0) {
              fs.writeFileSync(iconPath, buffer);
              console.log(`✅ Favicon téléchargé: ${iconPath}`);
              resolve(iconPath);
            } else {
              console.warn(`⚠️  Favicon vide pour ${appName}`);
              resolve(null);
            }
          });
        } else {
          console.warn(`⚠️  Échec du téléchargement du favicon pour ${appName}`);
          resolve(null);
        }
      }).on('error', () => {
        console.warn(`⚠️  Erreur favicon pour ${appName}`);
        resolve(null);
      });

      request.setTimeout(5000, () => {
        request.destroy();
        console.warn(`⚠️  Timeout favicon pour ${appName}`);
        resolve(null);
      });

    } catch (error) {
      console.warn(`⚠️  Erreur URL favicon pour ${appName}: ${error.message}`);
      resolve(null);
    }
  });
}

function generateAppManifest(appConfig) {
  const template = fs.readFileSync(
    'manifests/app-template.yml',
    'utf8'
  );

  let iconSource = [];

  // Check which icon files exist for this app
  const possibleExtensions = ['.png', '.svg', '.ico', '.jpg', '.jpeg'];

  for (const ext of possibleExtensions) {
    const iconPath = path.join(iconsDir, `${appConfig.appName}${ext}`);
    if (fs.existsSync(iconPath)) {
      iconSource.push(`      - type: file\n        path: ../icons/${appConfig.appName}${ext}\n        dest-filename: com.tekkengreg.bigbrowser.${appConfig.appName}${ext}`);
      break; // Only use the first icon found
    }
  }

  if (iconSource.length === 0) {
    iconSource.push('      []  # No icon available');
  }

  return template
    .replace(/APPNAME/g, appConfig.appName)
    .replace(/APP_DISPLAY_NAME/g, appConfig.displayName)
    .replace(/APP_DESCRIPTION/g, appConfig.description)
    .replace(/APP_URL/g, appConfig.url)
    .replace(/ICON_URL/g, appConfig.iconUrl)
    .replace(/APP_CATEGORIES/g, appConfig.categories)
    .replace(/APP_KEYWORDS/g, appConfig.keywords)
    .replace(/      # ICON_SOURCE will be replaced by the generator/g, iconSource.join('\n'));
}

async function generateAllApps() {
  console.log('🔄 Génération des manifestes Flatpak avec icônes...\n');

  for (const [appKey, appConfig] of Object.entries(appConfigs)) {
    const fileName = `manifests/com.tekkengreg.bigbrowser.${appConfig.appName}.yml`;

    const content = generateAppManifest(appConfig);
    fs.writeFileSync(fileName, content);
    console.log(`✅ Généré: ${fileName}`);
  }

  console.log('\n🎉 Tous les manifestes ont été générés avec succès !');
  console.log('\n📦 Pour build l\'application de base et les applications :');
  console.log('   1. Build de l\'app base: pnpm run build:base');
  console.log('   2. Install de l\'app base: pnpm run install:base');
  console.log('   3. Build des apps: pnpm run build:flatpak:all:optimized');
}

async function addNewApp(name, displayName, url, iconUrl, description, categories, keywords) {
  const appConfig = {
    appName: name,
    displayName: displayName,
    description: description || `${displayName} web application`,
    url: url,
    iconUrl: iconUrl,
    categories: categories || 'Network;WebBrowser;',
    keywords: keywords || `${name};web;browser;`
  };

  if (iconUrl) {
    await downloadIcon(iconUrl, name);
  }

  const fileName = `manifests/com.tekkengreg.bigbrowser.${name}.yml`;
  const content = generateAppManifest(appConfig, true);

  fs.writeFileSync(fileName, content);
  console.log(`✅ Nouvelle application générée: ${fileName}`);

  return appConfig;
}

function buildAllApps() {
  console.log('🔄 Build de toutes les applications Flatpak...\n');

  for (const [appKey, appConfig] of Object.entries(appConfigs)) {
    const fileName = `manifests/com.tekkengreg.bigbrowser.${appConfig.appName}.yml`;
    console.log(`🔨 Building ${appConfig.appName}...`);

    exec(`flatpak-builder --repo=repo --force-clean build-dir-${appConfig.appName} ${fileName}`, (error, stdout, stderr) => {
      if (error) {
        console.error(`❌ Erreur lors du build de ${appConfig.appName}: ${error.message}`);
        return;
      }
      console.log(`✅ Build terminé: ${appConfig.appName}`);
    });
  }

  console.log('\n🎉 Lancement de tous les builds !');
}

async function updateIcons() {
  console.log('🔄 Mise à jour de toutes les icônes...\n');

  for (const [appKey, appConfig] of Object.entries(appConfigs)) {
    if (appConfig.iconUrl) {
      await downloadIcon(appConfig.iconUrl, appConfig.appName);
    }
  }

  console.log('\n✅ Toutes les icônes ont été mises à jour !');
}

// CLI Interface
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === 'all') {
    generateAllApps(true).catch(console.error);
  } else if (args[0] === 'add' && args.length >= 4) {
    const [, name, displayName, url, iconUrl, description, categories, keywords] = args;
    addNewApp(name, displayName, url, iconUrl, description, categories, keywords).catch(console.error);
  } else if (args[0] === 'build') {
    buildAllApps();
  } else if (args[0] === 'update-icons') {
    updateIcons().catch(console.error);
  } else {
    console.log('Usage:');
    console.log('  node generate-app.js [all]                    - Génère toutes les applications avec icônes');
    console.log('  node generate-app.js update-icons             - Met à jour toutes les icônes');
    console.log('  node generate-app.js add <n> <displayName> <url> <iconUrl> [description] [categories] [keywords]');
    console.log('  node generate-app.js build                    - Build toutes les applications');
    console.log('');
    console.log('Exemple:');
    console.log('  node generate-app.js add discord "Discord" "https://discord.com/app" "https://discord.com/assets/icon.png"');
  }
}

module.exports = { generateAppManifest, addNewApp, appConfigs, downloadIcon, updateIcons }; 