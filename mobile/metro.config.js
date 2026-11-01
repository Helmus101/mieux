const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const sharedRoot = path.resolve(projectRoot, '../shared');
const config = getDefaultConfig(projectRoot);

// shared/ lives outside the app folder and has no node_modules of its own: watch it and resolve its imports from mobile/node_modules.
config.watchFolders = [sharedRoot];
config.resolver.nodeModulesPaths = [path.resolve(projectRoot, 'node_modules')];
config.resolver.extraNodeModules = new Proxy({}, { get: (_, name) => path.join(projectRoot, 'node_modules', String(name)) });
module.exports = config;
