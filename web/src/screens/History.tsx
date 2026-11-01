import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useHistory } from '@shared/stores';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Section, Group, Cell, Row, Pill } from '../ui';
import { routes, useNav } from '../nav';

const when = (iso: string) => new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });

export default function History() {
  const { go, back } = useNav();
  const h = useHistory();
  const clear = async () => { if (confirm(t('history.clearConfirm'))) { h.clear(); await api.deleteAccount().catch(() => undefined); } };
  return (
    <Screen>
      <NavBar onBack={back} title={t('history.title')} />
      <LargeTitle sub={t('history.local')}>{t('history.title')}</LargeTitle>
      <Section title={`${t('history.scans')} (${h.scans.length})`}>
        {h.scans.length ? <Group>{h.scans.slice(0, 50).map((s) => (
          <Cell key={s.at} image={s.product.imageUrl ?? ''} chevron onPress={() => go(routes.product(s.id))}><b>{s.product.name}</b><Muted>{s.product.brand} · {when(s.at)}</Muted></Cell>
        ))}</Group> : <Card><Muted>{t('history.none')}</Muted></Card>}
      </Section>
      <Section title={`${t('history.searches')} (${h.searches.length})`}>
        {h.searches.length ? h.searches.slice(0, 20).map((s) => (
          <Card key={s.id}><Row spread><b>{s.originalName}</b><Muted>{when(s.at)}</Muted></Row>
            <div>{s.priorities.map((p) => <Pill key={p} tone="g">{t('priorities.' + p)}</Pill>)}</div>
            {s.results.map((r) => <Row spread key={r.id}><span className="sm">{r.name}</span><span className="mut sm">{r.priceCents != null ? formatCents(r.priceCents * 10) + ' / kg ou L' : ''}</span></Row>)}
            <Button small plain onPress={() => go(routes.alternatives(s.originalId))}>{t('alt.run')}</Button></Card>
        )) : <Card><Muted>{t('history.none')}</Muted></Card>}
      </Section>
      <Section title={`${t('history.comparisons')} (${h.comparisons.length})`}>
        {h.comparisons.length ? <Group>{h.comparisons.slice(0, 20).map((c) => <Cell key={c.at}><b>{c.names.map((n) => n.slice(0, 22)).join(' · ')}</b><Muted>{when(c.at)}</Muted></Cell>)}</Group> : <Card><Muted>{t('history.none')}</Muted></Card>}
      </Section>
      <Button danger onPress={clear}>{t('history.clear')}</Button>
    </Screen>
  );
}
