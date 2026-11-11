import { useEffect, useState } from 'react';
import { t } from '@shared/i18n';
import { toast } from './toast';

/** A thin bar under the status bar while the phone is offline; a short toast when the connection comes back. */
export default function NetStatus() {
  const [off, setOff] = useState(() => typeof navigator !== 'undefined' && navigator.onLine === false);
  useEffect(() => {
    const down = () => setOff(true);
    const up = () => { setOff((was) => { if (was) toast(t('net.online')); return false; }); };
    window.addEventListener('offline', down); window.addEventListener('online', up);
    return () => { window.removeEventListener('offline', down); window.removeEventListener('online', up); };
  }, []);
  if (!off) return null;
  return <div className="netbar" role="status" aria-live="polite">{t('net.offline')}</div>;
}
