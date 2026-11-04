/** Detect if the device is mobile/tablet vs desktop. */
export const isDesktop = () => {
  const ua = navigator.userAgent;
  return !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
};

/** Get the app URL for QR code linking. */
export const getAppUrl = () => {
  const origin = window.location.origin;
  return origin + '/app';
};
