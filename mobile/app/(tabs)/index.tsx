import { useCallback, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { api } from '@shared/api/client';
import { getApiBase } from '@shared/config';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { formatCents } from '@shared/utils/format';
import { Bar, Button, Card, Collapsible, CountUp, Group, Cell, Hero, Muted, Pill, Row, Screen, Skeleton, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Home() {
  const c = useTheme();
  const { go } = useNav();
  const { name, place } = useProfile();
  const [d, setD] = useState<any>(null), [bg, setBg] = useState<any>(null), [err, setErr] = useState('');
  useFocusEffect(useCallback(() => { api.getInsights().then(setD).catch((e: Error) => setErr(e.message)); api.getBudget().then(setBg).catch(() => undefined); }, []));
  const B = bg?.budget, st = B?.status, top = d?.opportunities?.[0];
  return (
    <Screen>
      <Hero title={name ? t('about.hello', { n: name }) : t('home.title')} sub={place ? place.city : t('home.sub')}>
        <View style={{ marginTop: 14 }}><Button onPress={() => go(routes.scan)}>{t('home.scanProduct')}</Button></View>
      </Hero>
      {bg && !B && <Card tint><Text style={{ color: c.ink, fontWeight: '600' }}>{t('bud.setup')}</Text><Muted>{t('bud.setupText')}</Muted><Button small onPress={() => go(routes.profile)}>{t('bud.setup')}</Button></Card>}
      {st && (
        <Card>
          <Row spread><Muted>{t('bud.' + (B.config.period === 'weekly' ? 'weekLabel' : B.config.period === 'monthly' ? 'monthLabel' : 'tripLabel'))}</Muted><Pill tone={st.label === 'on_track' ? undefined : st.label === 'watch' ? 'w' : 'b'}>{t('bud.' + st.label)}</Pill></Row>
          <CountUp value={st.spent_cents} format={(v) => formatCents(Math.round(v))} />
          <Muted>{t('bud.of', { b: formatCents(st.budget_cents) })}</Muted>
          <View style={{ marginVertical: 10 }}><Bar value={Math.min(1, st.used_pct / 100)} /></View>
          <Text style={{ color: c.ink }}><Text style={{ fontWeight: '700' }}>{formatCents(Math.max(0, st.remaining_cents))}</Text> {t('bud.remaining')}</Text>
          {st.forecast?.will_exceed ? <Text style={{ color: c.bad, fontSize: 13, marginTop: 6 }}>{t('fc.exceed', { p: formatCents(st.forecast.projected_cents) })}</Text> : null}
        </Card>)}
      {top && (
        <Card tint>
          <Muted>{t('simple.topPick')}</Muted>
          <Text style={{ color: c.accent, fontSize: 28, fontWeight: '800' }}>−{formatCents(top.saving_per_purchase_cents)} <Text style={{ fontSize: 15, fontWeight: '500' }}>{t('home.savePer')}</Text></Text>
          <Text style={{ color: c.ink, marginTop: 4 }}><Text style={{ fontWeight: '600' }}>{top.product.name}</Text> → <Text style={{ fontWeight: '600' }}>{top.alternative.name}</Text></Text>
          <Button small onPress={() => go(routes.product(top.alternative.id))}>{t('home.explore')}</Button>
        </Card>)}
      {!d && !err && <Skeleton h={90} />}
      {err ? <Card><Muted>{t('home.loadFail', { e: err })}</Muted><Muted small>Serveur : {getApiBase()}</Muted></Card> : null}
      <Button onPress={() => go(routes.receipt)}>{t('home.scanReceipt')}</Button>
      {d && !d.opportunities?.length && d.top_products?.length === 0 && <Card tint><Text style={{ color: c.ink, fontWeight: '600' }}>{t('home.startTitle')}</Text><Muted>{t('home.startText')}</Muted></Card>}
      {(d?.categories?.length > 0 || d?.top_products?.length > 0) && (
        <Collapsible title={t('simple.seeMore')}>
          {d.categories?.map((x: any) => (<View key={x.category} style={{ marginVertical: 6 }}><Row spread><Text style={{ color: c.ink }}>{x.category}</Text><Muted small>{formatCents(x.spend_cents)}</Muted></Row><Bar value={x.share} /></View>))}
          {d.top_products?.length > 0 && <Group>{d.top_products.map((p: any, i: number) => <Cell key={p.name} last={i === d.top_products.length - 1}><Row spread><Text style={{ color: c.ink, flex: 1 }}>{p.name}</Text><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(p.spend_cents)}</Text></Row></Cell>)}</Group>}
        </Collapsible>)}
    </Screen>
  );
}
