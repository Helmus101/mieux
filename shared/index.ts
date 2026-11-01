// Main entry point for shared package

export * from './types';
export * from './api/client';
export * from './stores/authStore';
export * from './stores/preferencesStore';
export * from './utils/format';

// Re-export api client directly for convenience
export { api } from './api/client';
