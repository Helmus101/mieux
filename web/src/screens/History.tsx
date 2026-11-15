import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { useState } from 'react';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Section, Group, Cell, Confirm } from '../ui';
import { routes, useNav } from '../nav';

const when = (iso: string) => new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });

export default function History() {
  const { go, back } = useNav();
  const h = useHistory();
  const [ask, setAsk] = useState(false);
  const clear = async () => { h.clear(); await api.deleteAccount().catch(() => undefined); };
  return (
    <Screen>
      <NavBar onBack={back} />
      <LargeTitle sub={t('history.local')}>{t('history.title')}</LargeTitle>
      <Section title={`${t('history.scans')} (${h.scans.length})`}>
        {h.scans.length ? <Group>{h.scans.slice(0, 50).map((s) => (
          <Cell key={s.at} image={s.product.imageUrl ?? ''} chevron onPress={() => go(routes.product(s.id))}><b>{s.product.name}</b><Muted>{s.product.brand} · {when(s.at)}</Muted></Cell>
        ))}</Group> : <Card><Muted>{t('history.none')}</Muted></Card>}
      </Section>
      <Button danger onPress={() => setAsk(true)}>{t('history.clear')}</Button>
      <Confirm open={ask} onClose={() => setAsk(false)} onConfirm={clear} title={t('history.clear')} action={t('common.delete')}>{t('history.clearConfirm')}</Confirm>
    </Screen>
  );
}
