import { useEffect, useState } from 'react';
import { Image, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents, isLiquid } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { Button, Card, Collapsible, Muted, NovaBadge, NutriScore, Pill, Row, Screen, Segmented, Skeleton, Toast, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import * as hx from '../../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const eur = (v: number | null | undefined) => (v == null ? '—' : v.toFixed(2).replace('.', ',') + ' €');
const saveBy = (r: any, per100: number | null | undefined) => { const o = r?.original_price; if (!o || o.pack_cents == null || per100 == null || !o.per100_cents) return 0; return Math.max(0, Math.round((o.per100_cents - per100) * o.pack_cents / o.per100_cents)); };
const NEAR_KM = 5; // same radius as the web app

export default function Alternatives() {
  const c = useTheme();
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const { go, back } = useNav();
  const saved = useProfile((s) => s.priorities), estimates = useProfile((s) => s.estimates), addCompare = useProfile((s) => s.addCompare);
  const home = useProfile((s) => s.place);
  const myChains = useProfile((s) => s.chains) ?? [];
  const hasHome = home?.lat != null;
  const addSearch = useHistory((s) => s.addSearch);
  // Same request as the web screen: quality priorities only (the money tabs come from the rankings), close substitutes only,
  // the same 5 km radius and the same chain scope. The screen must not invent a second set of rules.
  const prios = (() => { const q = saved.filter((k) => k !== 'budget' && k !== 'value'); return q.length ? q : ['overall']; })();
  const mode = 'similar', pc = 'any';
  const [rk, setRk] = useState('closest'), [touched, setTouched] = useState(false);
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState('');
  const [expl, setExpl] = useState<Record<string, any>>({}), [chosen, setChosen] = useState<string[]>([]), [note, setNote] = useState<string | null>(null);
  const [stores, setStores] = useState<Record<string, any[]>>({});
  useEffect(() => {
    if (!barcode || !prios.length) return;
    setBusy(true); setErr('');
    api.getAlternatives(barcode, { priorities: prios, category_mode: mode, limit: 10, price_constraint: pc, substitution_max: 2, same_size: false, approximate: estimates, chains: myChains, ...(hasHome ? { location: { lat: home!.lat, lon: home!.lon, radius_km: NEAR_KM } } : {}) })
      .then((x: any) => { setR(x); if (!touched && !(x.rankings?.closest?.length) && x.budget?.recommended_ranking) setRk(x.budget.recommended_ranking); addSearch({ originalId: barcode, originalName: x.original?.name ?? barcode, priorities: prios, mode, results: (x.alternatives ?? []).map((a: any) => ({ id: a.product_id, name: a.product.name, brand: a.product.brand, priceCents: a.price_per_100_cents != null ? Math.round(a.price_per_100_cents) : null })) }); })
      .catch((e: Error) => setErr(e.message)).finally(() => setBusy(false));
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, myChains.join()]);
  // Same "Où le trouver" block as the web app: exact-shop observations near home, with their date. No stock claim.
  useEffect(() => {
    const lat = home?.lat, lon = home?.lon;
    if (!r || lat == null || lon == null) return;
    let alive = true;
    const codes: string[] = (r.rankings?.closest ?? []).slice(0, 10).map((e: any) => e.product.barcode ?? e.product.id);
    Promise.all(codes.map((bc) => api.getStorePrices(bc, { lat, lon, radius_km: NEAR_KM }).then((x: any) => [bc, x.stores ?? []] as const).catch(() => [bc, []] as const)))
      .then((pairs) => { if (alive) setStores(Object.fromEntries(pairs)); });
    return () => { alive = false; };
  }, [r, home?.lat, home?.lon]);
  const explain = async (id: string) => { setExpl((e) => ({ ...e, [id]: { loading: true } })); try { const x = await api.explain(barcode!, id); setExpl((e) => ({ ...e, [id]: x })); } catch { setExpl((e) => ({ ...e, [id]: null })); } };
  // Same four rankings as the web app: closest (default), budget, value, quality. "match" shows the quality ranking, never the priority list.
  const listOf = (k: string) => (r?.rankings?.[k === 'match' ? 'quality' : k] ?? []).filter((e: any) => {
    if (k === 'closest') return true;                                    // genuine substitutes, price or availability not required
    const q = r?.original?.score?.total != null && e.product.score?.total != null ? e.product.score.total - r.original.score.total : null;
    if (k === 'match') return q == null || q >= 0;                       // equal or better quality
    return e.price_per_100_cents != null;                                // money tabs: a real price is required
  }).map((e: any) => ({ product: e.product, why: e.why, tradeoffs: e.tradeoffs ?? [], price100: e.price_per_100_cents, estimated: e.estimated, dominated: e.dominated, sizes: e.other_sizes, conf: e.price_source?.confidence as string | undefined, avail: e.availability }));
  const entries = listOf(rk);
  return (
    <Screen>
      <Button small plain onPress={back}>‹ {t('common.back')}</Button>
      <Text style={{ color: c.ink, fontSize: 30, fontWeight: '800' }}>{t('alt.title')}</Text>
      {r?.original && <Muted>{r.original.name}</Muted>}
      <Segmented value={rk} onChange={(k) => { setTouched(true); setRk(k); }} options={[{ key: 'closest', label: t('rank.closest') }, { key: 'budget', label: t('rank.budget') }, ...(listOf('value').length ? [{ key: 'value', label: t('rank.value') }] : []), ...(listOf('match').length ? [{ key: 'match', label: t('rank.match') }] : [])]} />
      <Muted small>{t('rank.' + rk + 'Sub')}</Muted>
      {busy && <><Skeleton h={150} /><Skeleton h={150} /></>}
      {err ? <Card><Muted>{err}</Muted></Card> : null}
      {r && !busy && !entries.length && <Card><Text style={{ color: c.ink, fontWeight: '600' }}>{rk === 'match' ? r.no_recommendation_reason : t('rank.empty')}</Text><Muted small>{t('simple.tryFilters')}</Muted></Card>}
      {r && !busy && entries.map((e: any, i: number) => {
        const sv = saveBy(r, e.price100);
        return (
          <Card key={e.product.id}>
            <Row>{e.product.imageUrl ? <Image source={{ uri: e.product.imageUrl }} style={{ width: 60, height: 60, borderRadius: 14, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
              <View style={{ flex: 1 }}><Text style={{ color: c.ink, fontWeight: '700', fontSize: 16 }}>{i === 0 ? '★ ' : ''}{e.product.name}</Text><Muted small>{e.product.brand}</Muted></View></Row>
            <Row wrap style={{ marginTop: 8 }}><NutriScore grade={e.product.nutriScore} /><NovaBadge group={e.product.novaGroup} estimated={e.product.novaEstimated} />{e.estimated ? <Pill tone="w">{t('est.pill')}</Pill> : null}{e.conf && !e.estimated ? <Pill tone={e.conf === 'low' ? 'w' : 'g'}>{t('alt.conf_' + e.conf)}</Pill> : null}{e.dominated ? <Pill tone="g">{t('simple.dominated')}</Pill> : null}{e.avail && e.avail.state !== 'unknown' ? <Pill tone={e.avail.state === 'observed_at_store' ? 'g' : 'w'}>{e.avail.state === 'observed_at_store' ? t('avail.observed', { s: e.avail.store ?? '?', d: e.avail.date ?? '' }) : e.avail.state === 'seen_at_chain' ? t('avail.chain') : t('avail.listed')}</Pill> : null}</Row>
            {e.price100 != null ? (
              <Row spread style={{ marginTop: 8, alignItems: 'baseline' }}>
                <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700' }}>{eur(e.price100 / 100 * 10)} / {isLiquid(e.product) ? 'L' : 'kg'}</Text>
                {sv > 0 ? <Text style={{ color: c.accent, fontSize: 16, fontWeight: '700' }}>−{eur(sv / 100)} {t('simple.perPack')}</Text> : null}
              </Row>
            ) : sv > 0 ? (
              <Text style={{ color: c.accent, fontSize: 20, fontWeight: '800', marginTop: 8 }}>−{eur(sv / 100)} <Text style={{ fontSize: 14, fontWeight: '500' }}>{t('simple.perPack')}</Text></Text>
            ) : null}
            <Text style={{ color: c.ink, marginTop: 6 }}>{e.why || '—'}.</Text>
            <Collapsible title={t('simple.moreInfo')}>
              <Muted small>{t('alt.tradeoffs')} : {e.tradeoffs.join(' ; ')}.</Muted>
              {e.sizes > 0 ? <Muted small>{t('simple.sizes', { n: e.sizes })}</Muted> : null}
              {(stores[e.product.barcode ?? e.product.id] ?? []).length > 0 ? (
                <View>
                  <Muted small>{t('where.title')}</Muted>
                  {(stores[e.product.barcode ?? e.product.id] ?? []).slice(0, 3).map((s: any) => (
                    <View key={`${s.store}-${s.date}`} style={{ marginTop: 4 }}>
                      <Text style={{ color: c.ink, fontSize: 14 }}>{s.store} · {t('where.km', { d: s.distance_km })}</Text>
                      <Muted small>{t('where.seen', { d: s.date })} · {formatCents(s.pack_cents ?? Math.round((s.per100_cents ?? 0) * 10))}</Muted>
                    </View>
                  ))}
                  <Muted small>{t('where.stockNote')}</Muted>
                </View>
              ) : null}
              {expl[e.product.id]?.text ? <Card tint><Text style={{ color: c.ink }}>{expl[e.product.id].text}</Text><Muted small>{expl[e.product.id].source === 'llm' ? t('ex.llm') : t('ex.template')}</Muted></Card> : <Button small plain onPress={() => explain(e.product.id)}>{expl[e.product.id]?.loading ? t('ex.loading') : t('ex.button')}</Button>}
              <Row wrap><Button small onPress={() => go(routes.product(e.product.id))}>{t('home.explore')}</Button><Button small plain onPress={() => { addCompare(barcode!); addCompare(e.product.id); go(routes.compare); }}>{t('tabs.compare')}</Button></Row>
            </Collapsible>
            {sv > 0 && !chosen.includes(e.product.id) && <Button primary onPress={async () => { await api.chooseSaving({ original_id: barcode!, alt_id: e.product.id, expected_saving_cents: sv, original_per100_cents: r.original_price.per100_cents }); setChosen((x) => [...x, e.product.id]); hx.success(); setNote(t('sav.chosenDone')); setTimeout(() => setNote(null), 2000); }}>{t('sav.buy')}</Button>}
          </Card>);
      })}
      <Toast text={note} />
    </Screen>
  );
}
