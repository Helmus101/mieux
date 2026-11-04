import { useEffect, useRef } from 'react';
import QRCode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { isDesktop, getAppUrl } from './mobileDetect';

export default function DesktopQRBanner() {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldShow = isDesktop();

  useEffect(() => {
    if (!shouldShow || !containerRef.current) return;

    try {
      const qr = QRCode(4, 'L');
      qr.addData(getAppUrl());
      qr.make();
      containerRef.current.innerHTML = qr.createImgTag(8);
    } catch (e) {
      console.error('Failed to generate QR code:', e);
    }
  }, [shouldShow]);

  if (!shouldShow) return null;

  return (
    <div className="desktop-qr-banner">
      <div className="qr-content">
        <div className="qr-left">
          <h3>{t('home.mobileTitle')}</h3>
          <p>{t('home.mobileSub')}</p>
        </div>
        <div ref={containerRef} />
      </div>
    </div>
  );
}
