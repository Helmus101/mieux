// Is this a phone browser tab (not the installed app)? Drives the "add to home screen" hint.
export type Platform = 'ios' | 'android' | 'other';

export function platform(): Platform {
  if (typeof navigator === 'undefined') return 'other';
  const ua = navigator.userAgent;
  if (/iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) return 'ios';
  return /Android/i.test(ua) ? 'android' : 'other';
}

export const isInstalled = () => {
  try { return window.matchMedia('(display-mode: standalone)').matches || (navigator as unknown as { standalone?: boolean }).standalone === true; } catch { return false; }
};

/** Phone, in a normal browser tab: the case where the install hint helps. */
export const shouldHint = () => platform() !== 'other' && !isInstalled();

const KEY = 'mieux_install_hidden_until', DAYS = 14;
export const hintHidden = () => { try { return Number(localStorage.getItem(KEY) ?? 0) > Date.now(); } catch { return false; } };
export const hideHint = () => { try { localStorage.setItem(KEY, String(Date.now() + DAYS * 864e5)); } catch { /* storage unavailable */ } };

export const OPEN_EVENT = 'mieux:install';
export const openInstall = () => window.dispatchEvent(new Event(OPEN_EVENT));

/** A phone (not a tablet): phones go straight into the app, computers and iPads get the landing page first. */
export const isPhone = () => {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent;
  return /iPhone|iPod/.test(ua) || (/Android/i.test(ua) && /Mobile/i.test(ua));
};

const IN_APP = 'mieux_in_app';
export const wantsLanding = () => {
  if (typeof window === 'undefined' || isPhone() || isInstalled()) return false;
  if (window.location.pathname !== '/' || new URLSearchParams(window.location.search).has('app')) return false;  // deep links and ?app go straight to the app
  try { return sessionStorage.getItem(IN_APP) !== '1'; } catch { return true; }
};
export const enterApp = () => { try { sessionStorage.setItem(IN_APP, '1'); } catch { /* storage unavailable */ } };
