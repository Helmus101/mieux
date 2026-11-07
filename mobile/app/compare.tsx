import { useCallback, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { Button, Card, Cell, Group, LargeTitle, Muted, NavBar, NovaBadge, NutriScore, Row, Screen, Skeleton, useTheme } from '../src/ui';
import { routes, useNav } from '../src/nav';

/* eslint-disable @typescript-eslint/no-explicit-any */
const LABEL: Record<string, string> = { energyKcal100g: 'kcal', protein100g: 'protein', sugars100g: 'sugars', saturatedFat100g: 'sat', salt100g: 'salt', fiber100g: 'fibre' };
const short = (p: any) => (p.name.length > 28 ? p.name.slice(0, 27) + '…' : p.name);

/** The default view: each product's score and price, then what actually differs, with the trade-off said plainly (never a bare "winner"). */
function Summary({ products }: { products: any[] }) {
  const c = useTheme();
  const scored = products.filter((p) => typeof p.score === 'number');
  const priced = products.filter((p) => p.price);
  const top = scored.length > 1 ? scored.reduce((a, b) => (b.score > a.score ? b : a)) : null;
  const cheap = priced.length > 1 ? priced.reduce((a, b) => (b.price.per100_cents < a.price.per100_cents ? b : a)) : null;
  const tied = (list: any[], key: (p: any) => number, best: any) => list.filter((p) => key(p) === key(best)).length > 1;
  const q = top && !tied(scored, (p) => p.score, top) ? top : null, ch = cheap && !tied(priced, (p) => p.price.per100_cents, cheap) ? cheap : null;
  return (
    <>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {products.map((p) => (
          <View key={p.id} style={{ width: 140, backgroundColor: c.card, borderRadius: 16, padding: 12, marginRight: 8, alignItems: 'center' }}>
            <Text numberOfLines={2} style={{ color: c.mut, fontSize: 12, textAlign: 'center', minHeight: 32 }}>{short(p)}</Text>
            <Text style={{ color: c.ink, fontSize: 30, fontWeight: '700' }}>{typeof p.score === 'number' ? p.score : '—'}<Text style={{ fontSize: 13, color: c.mut }}>/100</Text></Text>
            <Text style={{ color: c.mut, fontSize: 12, textAlign: 'center' }}>{p.price ? `${formatCents(Math.round(p.price.per100_cents * 10))} ${t('compare.perKgShort')}` : t('compare.noPrice')}</Text>
          </View>
        ))}
      </ScrollView>
      <Card>
        <Text style={{ color: c.ink, fontWeight: '700', fontSize: 17, marginBottom: 6 }}>{t('compare.diffTitle')}</Text>
        {q ? <Text style={{ color: c.ink, marginVertical: 2 }}>{t('compare.winQuality', { n: short(q) })}</Text> : null}
        {ch ? <Text style={{ color: c.ink, marginVertical: 2 }}>{t('compare.winPrice', { n: short(ch) })}</Text> : null}
        {q && ch && q.id !== ch.id ? <Muted small>{t('compare.tradeoff')}</Muted> : null}
        {q && ch && q.id === ch.id ? <Muted small>{t('compare.bothWin')}</Muted> : null}
        {!q && !ch ? <Muted>{t('compare.close')}</Muted> : null}
      </Card>
    </>
  );
}

export default function Compare() {
  const c = useTheme();
  const { go } = useNav();
  const { compare, addCompare, removeCompare, clearCompare, estimates } = useProfile();
  const [r, setR] = useState<any>(null), [full, setFull] = useState(false);
  const scans = useHistory((s) => s.scans);
  const recent = scans.map((x) => x.product).filter((p, i, a) => a.findIndex((q) => q.id === p.id) === i);
  useFocusEffect(useCallback(() => {
    if (compare.length >= 2) api.compareProducts(compare, estimates).then(setR).catch(() => setR(null));
    else setR(null);
  }, [compare.join(), estimates]));

  const cell = (s: string, key: string, best?: boolean, w = 104) => (
    <Text key={key} style={{ width: w, padding: 6, color: best ? c.accent : c.ink, fontWeight: best ? '700' : '400' }}>{s}</Text>
  );

  return (
    <Screen>
      <NavBar title={t('compare.title')} />
      <LargeTitle>{t('compare.title')}</LargeTitle>
      {compare.length < 2 ? <Card><Muted>{t('compare.empty')}</Muted></Card> : null}
      {compare.length >= 2 && !r ? <Skeleton h={160} /> : null}
      {r ? <Summary products={r.products} /> : null}
      {r && !full ? <Button plain onPress={() => setFull(true)}>{t('compare.full')}</Button> : null}
      {r && full ? (
        <Card>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}><View>
            <View style={{ flexDirection: 'row' }}>
              {cell('', 'h0')}
              {r.products.map((p: any) => (
                <View key={p.id} style={{ width: 104, padding: 6 }}>
                  <Text numberOfLines={2} style={{ color: c.ink, fontWeight: '600' }}>{p.name.slice(0, 18)}</Text>
                  <Button small plain onPress={() => removeCompare(p.id)}>{t('compare.remove')}</Button>
                </View>
              ))}
            </View>
            <View style={{ flexDirection: 'row' }}>{cell(t('compare.nutriscore'), 'ns')}{r.products.map((p: any) => <View key={p.id} style={{ width: 104, padding: 6 }}><NutriScore grade={p.nutriScore} /></View>)}</View>
            <View style={{ flexDirection: 'row' }}>{cell(t('compare.perKg'), 'pk')}{r.products.map((p: any) => <View key={p.id} style={{ width: 104, padding: 6 }}>{p.price ? <><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(Math.round(p.price.per100_cents * 10))}</Text>{p.price.source === 'estimate' ? <Muted small>{t('est.pill')}</Muted> : null}</> : <Text style={{ color: c.ink }}>—</Text>}</View>)}</View>
            <View style={{ flexDirection: 'row' }}>{cell(t('compare.pack'), 'pa')}{r.products.map((p: any) => <View key={p.id} style={{ width: 104, padding: 6 }}><Text style={{ color: c.ink }}>{p.price?.pack_cents != null ? formatCents(p.price.pack_cents) : '—'}</Text></View>)}</View>
            <View style={{ flexDirection: 'row' }}>{cell(t('nova.title').split(' (')[0], 'nov')}{r.nova.map((g: number | null, i: number) => <View key={i} style={{ width: 104, padding: 6 }}><NovaBadge group={g} /></View>)}</View>
            {r.rows.map((row: any) => (
              <View key={row.field} style={{ flexDirection: 'row' }}>
                {cell(t('compare.' + LABEL[row.field]), row.field)}
                {row.values.map((v: number | null, i: number) => cell(v == null ? '—' : String(Math.round(v * 10) / 10), `${row.field}${i}`, row.favourable[i]))}
              </View>
            ))}
          </View></ScrollView>
          {r.micro.length > 0 ? <>
            <Text style={{ color: c.ink, fontWeight: '700', marginTop: 14, marginBottom: 4 }}>{t('micro.title')}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}><View>
              {r.micro.map((m: any) => (
                <View key={m.key} style={{ flexDirection: 'row' }}>
                  {cell(t('micro.' + m.key), m.key + 'k')}
                  {m.values.map((v: number | null, i: number) => cell(v == null ? '—' : `${v} ${m.unit} (${m.nrv_pct[i]}%)`, `${m.key}${i}`, m.favourable[i]))}
                </View>
              ))}
            </View></ScrollView>
            <Muted small>{t('micro.note')}</Muted>
          </> : null}
          <Muted small>{t('compare.note')}</Muted>
          <Button small plain danger onPress={clearCompare}>{t('compare.clear')}</Button>
        </Card>
      ) : null}
      <Button primary onPress={() => go(routes.scan + '?compare=1')}>{t('compare.scanAnother')}</Button>
      <Text style={{ color: c.mut, fontSize: 13, fontWeight: '600', marginTop: 22, marginBottom: 8 }}>{t('compare.pickRecent')}</Text>
      {recent.filter((p) => !compare.includes(p.id)).length
        ? <Group>{recent.filter((p) => !compare.includes(p.id)).slice(0, 10).map((p, i, a) => (
          <Cell key={p.id} last={i === a.length - 1} image={p.imageUrl ?? null} onPress={() => addCompare(p.id)}>
            <Text style={{ color: c.ink, fontWeight: '600' }}>{p.name}</Text>
            <Muted small>{[p.brand, p.score ? `${p.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted>
          </Cell>))}</Group>
        : <Card><Muted>{t('compare.noRecent')}</Muted></Card>}
      {compare.length > 0 ? <Group>{compare.map((id, i) => (
        <Cell key={id} last={i === compare.length - 1} onPress={() => removeCompare(id)}>
          <Row spread><Text style={{ color: c.ink }}>{scans.find((s) => s.id === id)?.product.name ?? id}</Text><Muted small>{t('compare.remove')}</Muted></Row>
        </Cell>))}</Group> : null}
    </Screen>
  );
}
