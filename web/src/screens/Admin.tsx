import { useEffect, useState } from 'react';
import { t } from '@shared/i18n';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Loader, Row } from '../ui';
import { ADMIN_EMAIL, adminStats, useAccount, type AdminStats } from '../account';
import { Navigate } from 'react-router-dom';
import { routes, useNav } from '../nav';

export default function Admin() {
  const { back } = useNav();
  const email = useAccount((a) => a.email);
  const [s, setS] = useState<AdminStats | null>(null), [err, setErr] = useState(false);
  const load = () => { setErr(false); adminStats().then(setS).catch(() => setErr(true)); };
  useEffect(() => { if (email === ADMIN_EMAIL) load(); }, [email]);
  if (email !== ADMIN_EMAIL) return <Navigate to={routes.home} replace />;
  return (
    <Screen>
      <NavBar onBack={back} title={t('admin.title')} />
      <LargeTitle>{t('admin.title')}</LargeTitle>
      {!s && !err && <Loader />}
      {err && <Card><b>{t('admin.error')}</b><Muted>{t('admin.errorWhy')}</Muted><Button small onPress={load}>{t('common.retry')}</Button></Card>}
      {s && <>
        <Card><Row spread><span>{t('admin.users')}</span><b style={{ fontSize: 34 }}>{s.users}</b></Row></Card>
        <Card><Row spread><span>{t('admin.scans')}</span><b style={{ fontSize: 34 }}>{s.scans}</b></Row><Muted>{t('admin.scansNote', { n: s.accounts_with_scans })}</Muted></Card>
        <Button plain onPress={load}>{t('admin.refresh')}</Button>
      </>}
    </Screen>
  );
}
