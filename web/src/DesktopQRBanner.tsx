import { useEffect, useRef } from 'react';
import QRCode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { isDesktop, getAppUrl } from './mobileDetect';

export default function DesktopQRBanner() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const shouldShow = isDesktop();

  useEffect(() => {
    if (!shouldShow || !canvasRef.current) return;

    try {
      const qr = QRCode(4, 'L');
      qr.addData(getAppUrl());
      qr.make();
      qr.drawCanvas(canvasRef.current, 8);
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
        <canvas ref={canvasRef} className="qr-code" />
      </div>
    </div>
  );
}
