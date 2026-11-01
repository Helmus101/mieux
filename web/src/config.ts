// Runtime configuration, set once by each platform at startup (web: Vite env, Expo: EXPO_PUBLIC_API_URL).
let apiBase = '/v1';
export const getApiBase = () => apiBase;
export const setApiBase = (u: string) => { apiBase = u.replace(/\/$/, ''); };

// Additive strictness (Yuka-like): read by the API client so every product request and every alternatives search uses the same mode.
let strictAdditives = true;
export const getStrict = () => strictAdditives;
export const setStrict = (v: boolean) => { strictAdditives = v; };
