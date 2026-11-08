import { useEffect, useRef, useState } from 'react';
import { Image, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents, isLiquid, unitPrice } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { Bar, Button, Card, ChainBadge, Loader, Muted, NavBar, NovaBadge, NutriScore, Pill, Row, Screen, Segmented, Sheet, Skeleton, Toast, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import Where from '../../src/Where';
import SaveButton from '../../src/SaveButton';
import { friendlyError } from '../../src/errors';
import * as hx from '../../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const NEAR_KM = 5; // only products sold at a chain with a branch within 5 km of home: fixed, not a setting
const sizeLabel = (q: { amount: number; unit: string }) => (q.amount >= 1000 ? `${Math.round(q.amount / 100) / 10} ${q.unit === 'ml' ? 'L' : 'kg'}`.replace('.', ',') : `${Math.round(q.amount)} ${q.unit}`);

/** Alternatives: the same four rankings, the same request and the same per-kilo / per-pack differences as the web screen. */
export default function Alternatives() {
  const c = useTheme();
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const { go, back } = useNav();
  const saved = useProfile((s) => s.priorities), estimates = useProfile((s) => s.estimates);
  const home = useProfile((s) => s.place);
  const hasHome = home?.lat != null;
  const country = useProfile((s) => s.country);
  const myChains = ((useProfile((s) => s.chains) ?? []) as string[]).filter((id) => chainsFor(country).some((x) => x.id === id));

  // "Today" filters start from the saved profile and never write back to it.
  const prios = (() => { const q = saved.filter((k) => k !== 'budget' && k !== 'value'); return q.length ? q : ['overall']; })();
  const [tries, setTry] = useState(0); const picked = useRef(false);
  const [detail, setDetail] = useState<any | null>(null);
  const radius = NEAR_KM, [diffBy, setDiffBy] = useState<'kg' | 'pack'>('kg');
  const sameSize = false, subMax = 2, mode = 'similar', pc = 'any';
  const [rk, setRk] = useState('value'), [hidden, setHidden] = useState<string[]>([]);
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  // Cards with no price: approximate web price (and supermarkets), fetched in batches of 8 and shown as each arrives.
  const [webP, setWebP] = useState<Record<string, any>>({});
  useEffect(() => {
    const rows = (['value', 'budget', 'quality'] as const).flatMap((k) => (r?.rankings?.[k] ?? []) as any[]);
    const want = [...new Set(rows.filter((e) => e.price_per_100_cents == null && e.product?.barcode && e.product.quantity).map((e) => e.product.barcode as string))].slice(0, 24);
    if (!want.length) return;
    let live = true;
    (async () => { for (let i = 0; i < want.length && live; i += 8) { try { const m = await api.getWebPrices(want.slice(i, i + 8)); if (live) setWebP((cur) => ({ ...cur, ...m })); } catch { /* keep going */ } } })();
    return () => { live = false; };
  }, [r]);

  useEffect(() => {
    if (!barcode || !prios.length) return;
    setBusy(true); setErr(null);
    api.getAlternatives(barcode, { priorities: prios, category_mode: mode, limit: 20, substitution_max: subMax, same_size: sameSize, chains: myChains, price_constraint: pc, approximate: estimates, ...(hasHome ? { location: { lat: home!.lat, lon: home!.lon, radius_km: NEAR_KM } } : {}) })
      .then((x: any) => setR(x))
      .catch((e: unknown) => setErr(friendlyError(e)))
      .finally(() => setBusy(false));
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries]);

  const rowOf = (e: any) => ({
    ps_web: e.price_source?.source === "web_search", avail: e.availability, product: e.product, why: e.why, tradeoffs: e.tradeoffs ?? [], price100: e.price_per_100_cents, estimated: e.estimated,
    dominated: e.dominated, vs: e.value_score, better: e.better_than_yours, conf: e.price_source?.confidence as string | undefined, priceDate: e.price_date ?? e.price_source?.date,
    stale: e.price_stale ?? e.price_source?.stale, size: e.size ?? e.product.quantity, pack: e.pack_cents, ratio: e.size_ratio,
  });
  const os = r?.original?.score?.total;
  const listOf = (k: string) => (r?.rankings?.[k === 'match' ? 'quality' : k] ?? []).map(rowOf).filter((e: any) => {
    if (hidden.includes(e.product.id)) return false;
    if (k === 'closest') return true;                              // genuine substitutes, price or availability not required
    const q = os != null && e.product.score?.total != null ? e.product.score.total - os : null;
    if (k === 'budget') { const op = r?.original_price?.per100_cents; return e.price100 != null && (op == null || e.price100 < op); }   // cheaper than yours only, cheapest first
    if (k === 'match') { const os0 = r?.original?.score?.total; return os0 == null || (e.product.score?.total ?? -1) > os0; }   // better quality only: never the same or lower
    { const ov = r?.rankings?.original_value_score; return e.price100 != null && (ov == null || e.vs == null || e.vs > ov); }   // value: only a better price-quality score than yours
  });
  // Products with a known supermarket come first (Quality and Price-quality tabs, each group in its own order); on the price tab the cheapest stays first and chains only break ties.
  const nCh = (e: any) => (e.product.chains?.length ?? 0);
  const ranked = (() => {
    const l = listOf(rk);
    if (rk === 'budget') return l.map((e: any, i: number) => [e, i] as const).sort((a: any, b: any) => (a[0].price100 - b[0].price100) || (nCh(b[0]) - nCh(a[0])) || (a[1] - b[1])).map((x: any) => x[0]);
    return [...l.filter((e: any) => nCh(e) > 0), ...l.filter((e: any) => nCh(e) === 0)];
  })();
  const shown = ranked.slice(0, 10);   // never more than 10 per tab, after the strict filters
  // Exactly three tabs, always: price-quality (opens first), price, quality.
  const tabs = [{ key: 'value', label: t('rank.value') }, { key: 'budget', label: t('rank.budget') }, { key: 'match', label: t('rank.match') }];
  useEffect(() => { if (r && !tabs.some((x) => x.key === rk)) setRk(tabs[0]?.key ?? 'value'); }, [r, tabs.map((x) => x.key).join()]);
  const nothingNear = hasHome && !!r && ['budget', 'value', 'quality'].every((k) => !(r.rankings?.[k]?.length));

  // Only the difference against the scanned product is shown in the list (per kilo/litre, or per pack); real prices are in the details.
  const showPrice = rk === 'budget' || rk === 'value';   // price differences belong to the price tabs only
  const diffOf = (e: any): { text: string; tone: string; sub?: string } | null => {
    const o = r?.original_price;
    if (!o || !showPrice) return null;
    const liquid = isLiquid(e.product) || r?.original_size?.unit === 'ml';
    const fmt = (x: number) => `${x < 0 ? '−' : '+'}${formatCents(Math.abs(Math.round(x)))}`;
    const tone = (x: number) => (Math.abs(x) < 1 ? c.mut : x < 0 ? c.accent : c.bad);
    if (diffBy === 'pack') {
      if (e.pack == null || o.pack_cents == null) return null;
      const x = e.pack - o.pack_cents;
      return { text: `${fmt(x)} ${t('diff.perPack')}`, tone: tone(x), sub: e.price100 != null ? (() => { const k = (e.price100 - o.per100_cents) * 10; return `${fmt(k)}${liquid ? '/L' : '/kg'}`; })() : undefined };
    }
    if (e.price100 == null) return null;
    const k = (e.price100 - o.per100_cents) * 10, pct = Math.round(((e.price100 - o.per100_cents) / o.per100_cents) * 100);
    return { text: `${fmt(k)}${liquid ? '/L' : '/kg'}`, tone: tone(k), sub: `${pct > 0 ? '+' : ''}${pct} % ${t('diff.vs')}` };
  };

  const detailBody = (e: any) => {
    const q = e.product.score?.total, oq = r?.original?.score?.total, dq = q != null && oq != null ? q - oq : null;
    const dif = diffOf(e), u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
    return (<>
      <View style={{ backgroundColor: c.tint, borderRadius: 14, padding: 12 }}>
        <Row spread>
          <View><Muted small>{t('alt.sumQ')}</Muted><Text style={{ color: c.ink, fontWeight: '800', fontSize: 22 }}>{q ?? '—'}</Text>{q != null ? <Bar value={q / 100} /> : null}
            {dq != null ? <Text style={{ color: dq > 0 ? c.accent : dq < 0 ? c.bad : c.mut, fontWeight: '600' }}>{dq === 0 ? t('score.same') : `${dq > 0 ? '+' : '−'}${Math.abs(dq)} ${t('score.pts')}`}</Text> : null}</View>
          {u ? <View><Muted small>{t('alt.sumP')}</Muted><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(u.perUnitCents)}/{u.unit === 'L' ? 'L' : 'kg'}</Text>{dif ? <Text style={{ color: dif.tone, fontSize: 13 }}>{dif.text}</Text> : null}</View> : null}
          {e.vs != null ? <View><Muted small>{t('alt.sumV')}</Muted><Text style={{ color: c.ink, fontWeight: '800', fontSize: 22 }}>{e.vs}</Text><Bar value={e.vs / 100} /></View> : null}
        </Row>
        {e.tradeoffs?.length > 0 ? <Row wrap style={{ marginTop: 10 }}>{e.tradeoffs.slice(0, 2).map((x: string) => <Pill key={x} tone="w">{x}</Pill>)}</Row> : null}
      </View>
      {u ? <Muted small style={{ marginTop: 8 }}>{t('diff.real')} : <Text style={{ color: c.ink, fontWeight: '700' }}>{t(u.unit === 'L' ? 'simple.perL' : 'simple.perKg', { p: formatCents(u.perUnitCents) })}</Text>{e.pack != null ? ` · ${t('size.pack', { s: e.size?.amount ? sizeLabel(e.size) : '' })} ${formatCents(e.pack)}` : ''}</Muted> : null}
      {e.dominated ? <Muted small>{t('alt.dominated')}</Muted> : null}
      <Row wrap style={{ marginVertical: 8 }}><NutriScore grade={e.product.nutriScore} /><NovaBadge group={e.product.novaGroup} estimated={e.product.novaEstimated} />
        {e.estimated ? <Pill tone="w">{t('est.pill')}</Pill> : null}
        {e.conf && !e.estimated ? <Pill tone={e.conf === 'low' ? 'w' : 'g'}>{t('alt.conf_' + e.conf)}</Pill> : null}
      </Row>
      <Row><Button primary onPress={() => { setDetail(null); go(routes.product(e.product.id)); }}>{t('alt.seeProduct')}</Button></Row>
      <Button small plain onPress={async () => {
        try { await api.substitutionVerdict(barcode!, e.product.id, 'not_comparable'); hx.warning(); setHidden((h) => [...h, e.product.id]); setDetail(null); setNote(t('sub.thanks')); setTimeout(() => setNote(null), 2000); }
        catch { /* offline: keep it */ }
      }}><Text>⚑ </Text>{t('sub.notComparable')}</Button>
      <Text style={{ color: c.ink, fontWeight: '700', marginTop: 18, marginBottom: 4 }}>{t('where.title')}</Text>
      <Where barcode={e.product.id} liquid={isLiquid(e.product)} />
      {e.product.chains?.length > 0 ? <Row wrap style={{ marginTop: 8 }}>{e.product.chains.slice(0, 6).map((id: string) => <ChainBadge key={id} id={id} />)}{e.product.chains.length > 6 ? <Muted small>+{e.product.chains.length - 6}</Muted> : null}</Row> : null}
    </>);
  };

  return (
    <Screen>
      <NavBar onBack={back} title={t('alt.title')} />
      <Text style={{ color: c.ink, fontSize: 30, fontWeight: '800', letterSpacing: -0.5 }}>{t('alt.title')}</Text>
      {r?.original ? <Row wrap style={{ marginTop: 2, marginBottom: 6 }}>
        <Muted>{r.original.name}</Muted>
        {r.original.categories?.length > 0 ? <Pill>{r.original.categories[r.original.categories.length - 1].replace(/^en:|^fr:/, '').replace(/-/g, ' ')}</Pill> : null}
      </Row> : null}
      {tabs.length > 1 ? <Segmented value={rk} onChange={(k) => { picked.current = true; setRk(k); }} options={tabs} /> : null}
      <Muted small>{t('rank.' + rk + 'Sub')}</Muted>
      {showPrice && r?.original_price ? <Segmented value={diffBy} onChange={(k) => setDiffBy(k as 'kg' | 'pack')} options={[{ key: 'kg', label: t('diff.byKg') }, { key: 'pack', label: t('diff.byPack') }]} /> : null}
      {showPrice && r?.original_price?.per100_cents != null ? <Text style={{ color: c.ink, fontSize: 14, marginBottom: 6 }}>{t('diff.yours')} : <Text style={{ fontWeight: '700' }}>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</Text>{r.original_size?.amount ? ` · ${sizeLabel(r.original_size)}` : ''}{r.original_price.pack_cents != null ? ` · ${formatCents(r.original_price.pack_cents)}` : ''}</Text> : null}

      {busy ? <><Loader steps={t('common.stepsAlt').split('|')} onRetry={() => setTry((n) => n + 1)} /><Skeleton h={120} /></> : null}
      {err ? <Card><Text style={{ color: c.ink, fontWeight: '700' }}>{err.title}</Text><Muted>{err.why}</Muted><Button small onPress={() => setTry((n) => n + 1)}>{t('errs.retry')}</Button></Card> : null}

      {r && !busy && !shown.length ? (() => {
        const m = nothingNear ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: radius }), action: <Button small onPress={() => go(routes.profile)}>{t('emptyAlt.nearAction')}</Button> }
          : rk === 'closest' ? { title: t('rank.noClosest'), why: t('rank.closestSub'), action: null }
          : rk === 'match' ? { title: t('emptyAlt.qualityTitle'), why: os != null ? t('emptyAlt.qualityWhy', { s: os }) : t('emptyAlt.qualityWhyNoScore'), action: null }
          : r?.rankings?.no_baseline ? { title: t('emptyAlt.noPriceTitle'), why: t('emptyAlt.noPriceWhy'), action: null }
          : rk === 'budget' ? { title: t('emptyAlt.cheaperTitle'), why: t('emptyAlt.cheaperWhy'), action: null }
          : { title: t('emptyAlt.valueTitle'), why: t('emptyAlt.valueWhy'), action: null };
        return <Card><Text style={{ color: c.ink, fontWeight: '700' }}>{m.title}</Text><Muted>{m.why}</Muted>{m.action}</Card>;
      })() : null}

      {r && !busy && rk === 'budget' && shown.length > 0 ? <Muted small>{t('alt.cheapestNote')}</Muted> : null}

      {r && !busy ? shown.map((e: any, i: number) => {
        const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
        const dif = diffOf(e);
        return (
          <Card key={e.product.id}>
            <Row>
              {e.product.imageUrl ? <Image source={{ uri: e.product.imageUrl }} style={{ width: 56, height: 56, borderRadius: 12, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
              <View style={{ flex: 1 }}><Text style={{ color: c.ink, fontWeight: '700' }}>{i + 1}. {e.product.name}</Text><Muted small>{e.product.brand}</Muted></View>
              <SaveButton product={e.product} />
            </Row>
            <Row spread style={{ marginTop: 8 }}>
              {e.product.score ? <View>
                <Text style={{ color: c.ink, fontSize: 26, fontWeight: '800' }}>{e.product.score.total}<Muted small> · {t('score.' + e.product.score.band)}</Muted></Text>
                {rk === 'match' && r?.original?.score ? (() => { const dd = e.product.score.total - r.original.score.total; return <Text style={{ color: dd > 0 ? c.accent : dd < 0 ? c.bad : c.mut, fontWeight: '600', fontSize: 13 }}>{dd === 0 ? t('score.same') : `${dd > 0 ? '+' : '−'}${Math.abs(dd)} ${t('score.pts')}`}</Text>; })() : null}
                {e.vs != null ? <Text style={{ color: e.better ? c.accent : c.mut, fontWeight: '700', fontSize: 13 }}>{t('score.pq')} {e.vs}{e.better != null ? ` · ${e.better ? t('score.pqBetter') : t('score.pqWorse')}` : ''}</Text> : null}
              </View> : <View />}
              <View style={{ alignItems: 'flex-end' }}>
                {u ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700' }}>{e.ps_web ? "~ " : ""}{formatCents(u.perUnitCents)}/{u.unit}{e.pack != null ? <Muted small> ({formatCents(e.pack)})</Muted> : null}</Text>
                  : e.pack != null ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700' }}>{formatCents(e.pack)}</Text> : null}
                {!u && e.pack == null && webP[e.product.barcode] ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700' }}>~ {formatCents(Math.round(webP[e.product.barcode].per100_cents * 10))}/{isLiquid(e.product) ? 'L' : 'kg'}<Muted small> {t('score.webPrice')}</Muted></Text> : null}
                {!u && e.pack == null && webP[e.product.barcode]?.value_score != null ? <Text style={{ color: c.mut, fontWeight: '600', fontSize: 13 }}>{t('score.pq')} ≈ {webP[e.product.barcode].value_score}</Text> : null}
                {dif ? <Text style={{ color: dif.tone, fontWeight: '600', fontSize: 13 }}>{dif.text}</Text> : null}
              </View>
            </Row>
            {!(e.product.chains?.length) && webP[e.product.barcode]?.chains?.length > 0 ? <Row wrap style={{ marginTop: 8 }}>{webP[e.product.barcode].chains.slice(0, 6).map((id: string) => <ChainBadge key={id} id={id} />)}</Row> : null}
            {e.product.chains?.length > 0 ? <Row wrap style={{ marginTop: 8 }}>{e.product.chains.slice(0, 6).map((id: string) => <ChainBadge key={id} id={id} />)}{e.product.chains.length > 6 ? <Muted small>+{e.product.chains.length - 6}</Muted> : null}</Row> : null}
            <Button small plain onPress={() => { hx.light(); setDetail(e); }}>{t('simple.moreInfo')}</Button>
          </Card>);
      }) : null}

      <Sheet open={!!detail} onClose={() => setDetail(null)} title={detail?.product.name}>{detail ? detailBody(detail) : null}</Sheet>
      <Toast text={note} />
    </Screen>
  );
}
