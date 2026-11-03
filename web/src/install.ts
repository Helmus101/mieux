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

// Dismissing the banner only lasts until the page is loaded again: it comes back on every fresh load until the app is installed.
let dismissed = false;
export const hintHidden = () => dismissed;
export const hideHint = () => { dismissed = true; };

export const OPEN_EVENT = 'mieux:install';
export const openInstall = () => window.dispatchEvent(new Event(OPEN_EVENT));

/** A phone (not a tablet): phones go straight into the app, computers and iPads get the landing page first. */
export const isPhone = () => {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent;
  return /iPhone|iPod/.test(ua) || (/Android/i.test(ua) && /Mobile/i.test(ua));
};

export const APP_PATH = '/app';

/** The landing page lives only at the root, and only on computers and iPads. Phones, deep links and ?app go straight to the app.
 *  The root always shows it: a computer never lands inside the app by surprise, not even in an installed window or a tab
 *  where the app was already opened. */
export const wantsLanding = () => {
  if (typeof window === 'undefined' || isPhone()) return false;
  return window.location.pathname === '/' && !new URLSearchParams(window.location.search).has('app');
};
