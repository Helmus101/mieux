import { useEffect, useState } from 'react';
import { ScrollView, View } from 'react-native';
import { useRouter } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { Body, Button, Card, Cell, Group, H, LargeTitle, Loader, Muted, NavBar, NovaBadge, NutriScore, Pill, Screen, Section, Thumb } from '@/components/ui';
import { toneColor, useTheme } from '@/lib/theme';

/* eslint-disable @typescript-eslint/no-explicit-any */
const LABEL: Record<string, string> = { energyKcal100g: 'kcal', protein100g: 'protein', sugars100g: 'sugars', saturatedFat100g: 'sat', salt100g: 'salt', fiber100g: 'fibre' };
const short = (p: any) => (p.name.length > 28 ? p.name.slice(0, 27) + '…' : p.name);

/** Each product's score and price, then what differs, with the trade-off said plainly (never a bare "winner"). */
function Summary({ products }: { products: any[] }) {
  const c = useTheme();
  const scored = products.filter((p) => typeof p.score === 'number'), priced = products.filter((p) => p.price);
  const top = scored.length > 1 ? scored.reduce((a, b) => (b.score > a.score ? b : a)) : null;
  const cheap = priced.length > 1 ? priced.reduce((a, b) => (b.price.per100_cents < a.price.per100_cents ? b : a)) : null;
  const tied = (list: any[], key: (p: any) => number, best: any) => list.filter((p) => key(p) === key(best)).length > 1;
  const q = top && !tied(scored, (p) => p.score, top) ? top : null, ch = cheap && !tied(priced, (p) => p.price.per100_cents, cheap) ? cheap : null;
  return <>
    <View style={{ flexDirection: 'row', gap: 10 }}>{products.map((p) => (
      <View key={p.id} style={{ flex: 1, backgroundColor: c.card, borderRadius: 16, padding: 10, alignItems: 'center', gap: 4 }}>
        <Thumb uri={p.imageUrl} size={56} />
        <Muted small style={{ textAlign: 'center' }}>{short(p)}</Muted>
        <Body bold style={{ fontSize: 24, color: typeof p.score === 'number' ? toneColor(p.score >= 65 ? 'g' : p.score >= 40 ? 'w' : 'b', c.dark) : c.mut }}>{typeof p.score === 'number' ? p.score : '—'}</Body>
        <Muted small>{p.price ? formatCents(Math.round(p.price.per100_cents * 10)) + ' ' + t('compare.perKgShort') : t('compare.noPrice')}{p.price?.source === 'estimate' ? ' · ' + t('est.pill') : ''}</Muted>
      </View>
    ))}</View>
    <Card>
      <H>{t('compare.diffTitle')}</H>
      {q && <Body>{t('compare.winQuality', { n: short(q) })}</Body>}
      {ch && <Body>{t('compare.winPrice', { n: short(ch) })}</Body>}
      {q && ch && q.id !== ch.id && <Muted small>{t('compare.tradeoff')}</Muted>}
      {q && ch && q.id === ch.id && <Muted small>{t('compare.bothWin')}</Muted>}
      {!q && !ch && <Muted>{t('compare.close')}</Muted>}
    </Card>
  </>;
}

export default function Compare() {
  const r = useRouter(), c = useTheme();
  const { compare, toggleCompare, removeCompare, clearCompare, estimates } = useProfile();
  const [res, setRes] = useState<any>(null), [full, setFull] = useState(false);
  const scans = useHistory((s) => s.scans);
  const recent = scans.map((x) => x.product).filter((p, i, a) => a.findIndex((q) => q.id === p.id) === i);
  useEffect(() => {
    if (compare.length >= 2) api.compareProducts(compare, estimates).then(setRes).catch(() => setRes(null)); else setRes(null);
  }, [compare, estimates]);
  const cellW = 110;
  return (
    <Screen title={t('compare.title')}>
      <NavBar />
      <LargeTitle>{t('compare.title')}</LargeTitle>
      {compare.length < 2 && <Card><Muted>{t('compare.empty')}</Muted></Card>}
      {compare.length >= 2 && !res && <Loader />}
      {res && <Summary products={res.products} />}
      {res && !full && <Button plain onPress={() => setFull(true)}>{t('compare.full')}</Button>}
      {res && full && <Card>
        <ScrollView horizontal>
          <View>
            <View style={{ flexDirection: 'row' }}><View style={{ width: cellW }} />{res.products.map((p: any) => <View key={p.id} style={{ width: cellW, padding: 4 }}><Body bold style={{ fontSize: 13 }}>{p.name.slice(0, 18)}</Body><Button small plain danger onPress={() => removeCompare(p.id)}>{t('compare.remove')}</Button></View>)}</View>
            {[
              [t('compare.nutriscore'), res.products.map((p: any) => <NutriScore key={p.id} grade={p.nutriScore} />)],
              [t('compare.perKg'), res.products.map((p: any) => <Body key={p.id} bold>{p.price ? formatCents(Math.round(p.price.per100_cents * 10)) : '—'}</Body>)],
              [t('compare.pack'), res.products.map((p: any) => <Body key={p.id}>{p.price?.pack_cents != null ? formatCents(p.price.pack_cents) : '—'}</Body>)],
              [t('nova.title').split(' (')[0], res.nova.map((g: number | null, i: number) => <NovaBadge key={i} group={g} />)],
              ...res.rows.map((row: any) => [t('compare.' + LABEL[row.field]), row.values.map((v: number | null, i: number) => <Body key={i} bold={row.favourable[i]} style={{ color: row.favourable[i] ? c.accent : c.ink }}>{v == null ? '—' : Math.round(v * 10) / 10}</Body>)]),
            ].map(([label, cells]: any, i: number) => (
              <View key={i} style={{ flexDirection: 'row', paddingVertical: 8, borderTopWidth: 1, borderTopColor: c.line, alignItems: 'center' }}>
                <View style={{ width: cellW }}><Muted>{label}</Muted></View>
                {cells.map((x: any, j: number) => <View key={j} style={{ width: cellW, paddingHorizontal: 4 }}>{x}</View>)}
              </View>
            ))}
          </View>
        </ScrollView>
        <Muted small>{t('compare.note')}</Muted>
        <Button small plain danger onPress={clearCompare}>{t('compare.clear')}</Button>
      </Card>}
      <Button primary onPress={() => r.push('/scan?compare=1')}>{t('compare.scanAnother')}</Button>
      <Section title={t('compare.pickRecent')}>
        {recent.length ? <Group>{recent.slice(0, 10).map((p) => (
          <Cell key={p.id} image={p.imageUrl ?? null} onPress={() => toggleCompare(p.id)} right={compare.includes(p.id) ? <Pill>✓</Pill> : undefined}>
            <Body bold>{p.name}</Body><Muted small>{[p.brand, p.score ? `${p.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted>
          </Cell>
        ))}</Group> : <Card><Muted>{t('compare.noRecent')}</Muted></Card>}
      </Section>
    </Screen>
  );
}
