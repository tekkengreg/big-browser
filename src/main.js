const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

// Log the app path and environment
console.log('App path:', app.getAppPath());
console.log('Is packaged:', app.isPackaged);
console.log('Process type:', process.type);
console.log('Process platform:', process.platform);
console.log('Process arch:', process.arch);

function createWindow() {
  console.log('Creating window...');
  
  // Get the URL from command line arguments or environment variable or use a default
  const appName = process.argv[2] || process.env.APP_NAME || 'BigBrowser';
  const url = process.argv[3] || process.env.APP_URL || 'https://notion.so';
  console.log('Loading app:', appName, 'at URL:', url);
  
  // Options spécialisées pour SketchUp
  let webPreferences = {
    nodeIntegration: false,
    contextIsolation: false,
    webSecurity: true,
    allowRunningInsecureContent: false,
    enableRemoteModule: true,
    worldSafeExecuteJavaScript: true
  };
  
  // Configuration spéciale pour SketchUp
  if (appName === 'SketchUp') {
    console.log('🎨 Configuration spécialisée pour SketchUp...');
    webPreferences = {
      ...webPreferences,
      webgl: true,
      experimentalFeatures: true,
      experimentalCanvasFeatures: true,
      enableBlinkFeatures: 'WebGL2',
      allowRunningInsecureContent: true
    };
  }
  
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    show: true,
    webPreferences: webPreferences
  });
  
  // If no specific URL provided, show help message
  if (!process.argv[3] && !process.env.APP_URL) {
    console.log('BigBrowser Base Application');
    console.log('This app provides the shared components for all BigBrowser apps.');
    console.log('Use individual BigBrowser apps like Google, Notion, SketchUp instead.');
    return;
  }
  
  // Load the URL
  win.loadURL(url);

  // Afficher la fenêtre une fois que le contenu est chargé
  win.webContents.on('did-finish-load', () => {
    console.log('Content loaded, showing window...');
    win.show();
    win.focus();
  });

  // Log any errors
  win.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });

  // Log window state changes
  win.on('show', () => console.log('Window shown'));
  win.on('hide', () => console.log('Window hidden'));
  win.on('focus', () => console.log('Window focused'));
  win.on('blur', () => console.log('Window blurred'));
  win.on('closed', () => {
    console.log('Window closed');
    win = null;
  });

  // Ouvrir les DevTools en mode développement
  // if (!app.isPackaged) {
  //   win.webContents.openDevTools();
  // }
}

// Gérer le démarrage de l'application
app.whenReady().then(() => {
  console.log('App is ready');
  createWindow();

  app.on('activate', () => {
    console.log('App activated');
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Gérer la fermeture de l'application
app.on('window-all-closed', () => {
  console.log('All windows closed');
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Log any uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

// Log any unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
}); 