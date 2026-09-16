const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

let backendProcess = null;
let mainWindow = null;
let backendPort = null;

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = address.port;
      server.close(() => resolve(port));
    });
  });
}

function enginePath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'engine', 'SugioLabsEngine.exe');
  }
  return path.join(__dirname, 'engine', 'SugioLabsEngine.exe');
}

async function waitForBackend(url, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(`${url}/api/v1/health`, { cache: 'no-store' });
      if (response.ok) return true;
    } catch (_) {
      // Backend is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  return false;
}

function stopBackend() {
  if (!backendProcess) return;
  try {
    backendProcess.kill();
  } catch (_) {
    // Best-effort shutdown during app quit.
  }
  backendProcess = null;
}

async function startBackend() {
  backendPort = await getFreePort();
  const exe = enginePath();

  backendProcess = spawn(exe, ['--port', String(backendPort)], {
    windowsHide: true,
    stdio: 'ignore',
    env: {
      ...process.env,
      SUGIO_DESKTOP: '1',
    },
  });

  backendProcess.once('exit', (code) => {
    if (!app.isQuitting && code !== 0) {
      dialog.showErrorBox(
        'Sugio Labs engine stopped',
        'The local Sugio Labs engine exited unexpectedly. Please restart the application.'
      );
    }
  });

  const baseUrl = `http://127.0.0.1:${backendPort}`;
  const ready = await waitForBackend(baseUrl);
  if (!ready) {
    stopBackend();
    throw new Error('Local Sugio Labs engine did not become ready.');
  }
  return baseUrl;
}

async function createMainWindow() {
  const baseUrl = await startBackend();

  mainWindow = new BrowserWindow({
    width: 1460,
    height: 920,
    minWidth: 1080,
    minHeight: 700,
    show: false,
    backgroundColor: '#0b1020',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (!url.startsWith(baseUrl)) {
      event.preventDefault();
      if (url.startsWith('http://') || url.startsWith('https://')) {
        shell.openExternal(url);
      }
    }
  });

  await mainWindow.loadURL(baseUrl);
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('before-quit', () => {
  app.isQuitting = true;
  stopBackend();
});

app.whenReady().then(async () => {
  app.setAppUserModelId('com.sugiolabs.desktop');
  try {
    await createMainWindow();
  } catch (error) {
    dialog.showErrorBox('Sugio Labs could not start', String(error && error.message ? error.message : error));
    app.quit();
  }

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      try {
        await createMainWindow();
      } catch (error) {
        dialog.showErrorBox('Sugio Labs could not start', String(error));
      }
    }
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') app.quit();
});
