import { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { isDesktop, isStandalone, getAppUrl } from './mobileDetect';

const DISMISSED_KEY = 'mieux-mobile-guidance-dismissed';

export default function DesktopQRBanner() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dismissed, setDismissed] = useState(false);
  const desktop = isDesktop();
  const standalone = !desktop && isStandalone();

  useEffect(() => {
    try {
      setDismissed(localStorage.getItem(DISMISSED_KEY) === '1');
    } catch {
      // Storage is optional; the guidance remains dismissible for this session.
    }
  }, []);

  useEffect(() => {
    if (!desktop || !containerRef.current) return;

    try {
      const qr = QRCode(4, 'L');
      qr.addData(getAppUrl());
      qr.make();
      containerRef.current.innerHTML = qr.createImgTag(5);
    } catch (e) {
      console.error('Failed to generate QR code:', e);
    }
  }, [desktop]);

  if (dismissed || standalone) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem(DISMISSED_KEY, '1');
    } catch {
      // Storage is optional.
    }
  };

  if (!desktop) {
    return (
      <aside className="mobile-web-banner" aria-label={t('home.mobileWebTitle')}>
        <button className="mobile-web-close" onClick={dismiss} aria-label={t('home.mobileWebClose')}>×</button>
        <h3>{t('home.mobileWebTitle')}</h3>
        <p>{t('home.mobileWebSub')}</p>
        <p className="mobile-web-steps">{t('home.mobileWebSteps')}</p>
      </aside>
    );
  }

  return (
    <aside className="desktop-qr-banner" aria-label={t('home.mobileTitle')}>
      <button className="mobile-web-close" onClick={dismiss} aria-label={t('home.mobileClose')}>×</button>
      <div className="qr-content">
        <div className="qr-left">
          <h3>{t('home.mobileTitle')}</h3>
          <p>{t('home.mobileSub')}</p>
        </div>
        <div ref={containerRef} />
      </div>
    </aside>
  );
}
