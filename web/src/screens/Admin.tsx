import { useEffect, useState } from 'react';
import { t } from '@shared/i18n';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Loader, Row } from '../ui';
import { ADMIN_EMAIL, adminRequestSync, adminStats, useAccount, type AdminStats } from '../account';
import { Navigate } from 'react-router-dom';
import { routes, useNav } from '../nav';

export default function Admin() {
  const { back } = useNav();
  const email = useAccount((a) => a.email);
  const [s, setS] = useState<AdminStats | null>(null), [err, setErr] = useState(false), [busy, setBusy] = useState(false), [done, setDone] = useState(false);
  const load = () => { setErr(false); adminStats().then(setS).catch(() => setErr(true)); };
  useEffect(() => { if (email === ADMIN_EMAIL) load(); }, [email]);
  if (email !== ADMIN_EMAIL) return <Navigate to={routes.home} replace />;
  const sync = async () => { setBusy(true); setDone(false); try { await adminRequestSync(); setDone(true); load(); } catch { setErr(true); } setBusy(false); };
  return (
    <Screen>
      <NavBar onBack={back} title={t('admin.title')} />
      <LargeTitle>{t('admin.title')}</LargeTitle>
      {!s && !err && <Loader />}
      {err && <Card><b>{t('admin.error')}</b><Muted>{t('admin.errorWhy')}</Muted><Button small onPress={load}>{t('common.retry')}</Button></Card>}
      {s && <>
        <Card><Row spread><span>{t('admin.users')}</span><b style={{ fontSize: 34 }}>{s.users}</b></Row></Card>
        <Card><Row spread><span>{t('admin.scans')}</span><b style={{ fontSize: 34 }}>{s.scans}</b></Row><Muted>{t('admin.scansNote', { n: s.accounts_with_scans })}</Muted></Card>
        <Card>
          <b>{t('admin.syncTitle')}</b><Muted>{t('admin.syncText')}</Muted>
          <Button primary disabled={busy} onPress={sync}>{busy ? t('common.loading') : t('admin.syncBtn')}</Button>
          {done && <p style={{ color: 'var(--accent)' }}>{t('admin.syncDone')}</p>}
          {s.sync_epoch > 0 && <p className="mut sm">{t('admin.lastSync', { d: new Date(s.sync_epoch * 1000).toLocaleString() })}</p>}
        </Card>
        <Button plain onPress={load}>{t('admin.refresh')}</Button>
      </>}
    </Screen>
  );
}
