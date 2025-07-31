#!/usr/bin/env node

const fs = require('fs');
const { exec, execSync } = require('child_process');
const path = require('path');
const https = require('https');
const http = require('http');

// Configuration des applications
const appConfigs = require('./flatpak_apps.json');

// Créer le dossier icons s'il n'existe pas
const iconsDBDir = './icons-db';
const iconsDir = './icons';
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

function generateAppManifest(appConfig) {
  const template = fs.readFileSync(
    'manifests/app-template.yml',
    'utf8'
  );

  let iconSource = [];

  // Check which icon files exist for this app

    const iconPath = path.join(iconsDBDir, `${appConfig.appName}.png`);
    const iconPathDest = path.join(iconsDir, `${appConfig.appName}.png`);
    if (fs.existsSync(iconPath)) {
      // Vérifier et redimensionner l'icône si nécessaire
      try {
        // Vérifier les dimensions de l'icône
        const dimensions = execSync(`identify -format "%wx%h" "${iconPath}"`, { encoding: 'utf-8' }).trim();
        console.log(`📏 ${appConfig.appName}.png: ${dimensions}`);
        
        const [width, height] = dimensions.split('x').map(Number);
        
        // Si l'icône n'est pas carrée ou n'est pas 128x128, la redimensionner
        if (width !== height || width !== 128 || height !== 128) {
          console.log(`🔧 Redimensionnement de ${appConfig.appName}.png de ${dimensions} vers 128x128`);
          execSync(`convert "${iconPath}" -resize 128x128! "${iconPathDest}"`);
          
          // Vérifier le nouveau dimensionnement
          const newDimensions = execSync(`identify -format "%wx%h" "${iconPathDest}"`, { encoding: 'utf-8' }).trim();
          console.log(`✅ Nouvelle taille: ${newDimensions}`);
        } else {
          execSync(`cp "${iconPath}" "${iconPathDest}"`);
          console.log(`✅ ${appConfig.appName}.png est déjà à la bonne taille`);
        }
      } catch (error) {
        console.log(`⚠️  Impossible de vérifier/redimensionner ${appConfig.appName}.png:`, error.message);
        console.log(`   Assurez-vous qu'ImageMagick est installé (sudo apt install imagemagick)`);
      }
      
      iconSource.push(`      - type: file\n        path: ../icons/${appConfig.appName}.png\n        dest-filename: com.tekkengreg.bigbrowser.${appConfig.appName}.png`);
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

async function generateAllAppManifests() {
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

async function buildAllApps() {
  console.log('🔄 Build de toutes les applications Flatpak...\n');

  for (const [appKey, appConfig] of Object.entries(appConfigs)) {
    const fileName = `manifests/com.tekkengreg.bigbrowser.${appConfig.appName}.yml`;
    console.log(`🔨 Building ${appConfig.appName}...`);
    await new Promise((resolve, reject)=>exec(`flatpak-builder --repo=repo --force-clean build-dir-${appConfig.appName} ${fileName}`, (error, stdout, stderr) => {
      if (error) {
        console.error(`❌ Erreur lors du build de ${appConfig.appName}: ${error.message}`);
        reject(error);
      }
      console.log(`✅ Build terminé: ${appConfig.appName}`);
      resolve();
    }));
  }

  console.log('\n🎉 Lancement de tous les builds !');
}

// CLI Interface
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === 'all') {
    generateAllAppManifests(true).catch(console.error);
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

module.exports = { generateAppManifest, appConfigs }; 