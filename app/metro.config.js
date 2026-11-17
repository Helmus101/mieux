// Metro: the app reuses the platform-free code in ../shared (API client, stores, i18n, theme) exactly as the web app does.
const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const root = __dirname;
const shared = path.resolve(root, '../shared');
const config = getDefaultConfig(root);

config.watchFolders = [shared];
// ../shared has no node_modules of its own: resolve its imports (zustand, axios) from the app.
config.resolver.nodeModulesPaths = [path.resolve(root, 'node_modules')];
config.resolver.extraNodeModules = { '@shared': shared };

module.exports = config;
