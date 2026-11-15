/** Detect if the device is mobile/tablet vs desktop. */
export const isDesktop = () => {
  const ua = navigator.userAgent;
  return !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
};

/** Detect whether the site is already running as an installed PWA. */
export const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);

/** Get the app URL for QR code linking. */
export const getAppUrl = () => {
  // A phone cannot reach localhost / LAN-only hosts, so a QR made there would just hang: point it at the public site.
  const { hostname, origin } = window.location;
  const local = /^(localhost|127\.|0\.0\.0\.0|\[::1\]|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(hostname) || hostname.endsWith('.local');
  const site = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_SITE_URL || 'https://mieuxmanger.vercel.app';
  return (local ? site : origin) + '/app';
};
