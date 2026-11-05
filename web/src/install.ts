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

// × hides the banner until the page is loaded again; "Plus tard" hides it for 5 days. Otherwise it shows on every fresh load.
const KEY = 'mieux_install_hidden_until', LATER_DAYS = 5;
let dismissed = false;
export const hintHidden = () => { if (dismissed) return true; try { return Number(localStorage.getItem(KEY) ?? 0) > Date.now(); } catch { return false; } };
export const hideHint = (later = false) => {
  dismissed = true;
  if (later) { try { localStorage.setItem(KEY, String(Date.now() + LATER_DAYS * 864e5)); } catch { /* storage unavailable */ } }
};

export const OPEN_EVENT = 'mieux:install';
export const openInstall = () => window.dispatchEvent(new Event(OPEN_EVENT));

/** Phone or tablet (touch device). */
export const isPhone = () => platform() !== 'other';

export const APP_PATH = '/app';

/** The landing page lives only at the root, on every device. Only the installed app on a phone or tablet skips it (the home-screen
 *  icon opens /app anyway). Deep links and ?app go straight to the app.
 *  A computer never lands inside the app by surprise, not even in an installed window or a tab where the app was already opened. */
export const wantsLanding = () => {
  if (typeof window === 'undefined' || (isPhone() && isInstalled())) return false;
  return window.location.pathname === '/' && !new URLSearchParams(window.location.search).has('app');
};
