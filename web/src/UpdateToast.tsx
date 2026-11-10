import { useEffect } from 'react';
import { t } from '@shared/i18n';
import { toast } from './toast';
import { SW_UPDATED } from './sw-client';

/** "New version available · Refresh": shown once when a new service worker takes over while the app is open. */
export default function UpdateToast() {
  useEffect(() => {
    const on = () => toast(t('net.update'), { undo: () => location.reload(), actionLabel: t('net.updateNow'), ms: 12000 });
    window.addEventListener(SW_UPDATED, on);
    return () => window.removeEventListener(SW_UPDATED, on);
  }, []);
  return null;
}
