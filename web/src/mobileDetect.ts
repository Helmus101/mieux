/** Detect if the device is mobile/tablet vs desktop. */
export const isDesktop = () => {
  const ua = navigator.userAgent;
  return !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
};

/** Detect whether the site is already running as an installed PWA. */
export const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);

/** Get the app URL for QR code linking. */
export const getAppUrl = () => {
  const origin = window.location.origin;
  return origin + '/app';
};
