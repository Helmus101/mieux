import { useState } from 'react';
import { useRouter } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { Body, Button, Cell, Confirm, Group, LargeTitle, Muted, NavBar, Screen, Section } from '@/components/ui';

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });

export default function History() {
  const r = useRouter(), h = useHistory();
  const [ask, setAsk] = useState(false);
  const clear = async () => { h.clear(); await api.deleteAccount().catch(() => undefined); };
  return (
    <Screen title={t('history.title')}>
      <NavBar />
      <LargeTitle sub={t('history.local')}>{t('history.title')}</LargeTitle>
      <Section title={`${t('history.scans')} (${h.scans.length})`}>
        {h.scans.length ? <Group>{h.scans.slice(0, 50).map((s) => (
          <Cell key={s.at} image={s.product.imageUrl ?? null} chevron onPress={() => r.push(`/product/${s.id}`)}>
            <Body bold>{s.product.name}</Body><Muted small>{[s.product.brand, when(s.at)].filter(Boolean).join(' · ')}</Muted>
          </Cell>
        ))}</Group> : <><Muted>{t('history.none')}</Muted><Button primary onPress={() => r.push('/scan')}>{t('tabs.scan')}</Button></>}
      </Section>
      {h.scans.length > 0 && <Button danger onPress={() => setAsk(true)}>{t('history.clear')}</Button>}
      <Confirm open={ask} onClose={() => setAsk(false)} onConfirm={clear} title={t('history.clear')} action={t('common.delete')}>{t('history.clearConfirm')}</Confirm>
    </Screen>
  );
}
