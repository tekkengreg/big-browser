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
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    show: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      // Ajout des préférences pour le mode production
      enableRemoteModule: true,
      worldSafeExecuteJavaScript: true
    }
  });

  // Get the URL from the environment variable or use a default
  const url = process.env.APP_URL || 'https://notion.so';
  console.log('Loading URL:', url);
  
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
  if (!app.isPackaged) {
    win.webContents.openDevTools();
  }
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