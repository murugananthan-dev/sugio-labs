const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('sugioDesktop', Object.freeze({
  platform: process.platform,
  desktop: true,
}));
