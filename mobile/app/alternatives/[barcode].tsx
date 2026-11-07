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
  const [rk, setRk] = useState('closest'), [hidden, setHidden] = useState<string[]>([]);
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    if (!barcode || !prios.length) return;
    setBusy(true); setErr(null);
    api.getAlternatives(barcode, { priorities: prios, category_mode: mode, limit: 10, substitution_max: subMax, same_size: sameSize, chains: myChains, price_constraint: pc, approximate: estimates, ...(hasHome ? { location: { lat: home!.lat, lon: home!.lon, radius_km: NEAR_KM } } : {}) })
      .then((x: any) => setR(x))
      .catch((e: unknown) => setErr(friendlyError(e)))
      .finally(() => setBusy(false));
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries]);

  const rowOf = (e: any) => ({
    avail: e.availability, product: e.product, why: e.why, tradeoffs: e.tradeoffs ?? [], price100: e.price_per_100_cents, estimated: e.estimated,
    dominated: e.dominated, vs: e.value_score, conf: e.price_source?.confidence as string | undefined, priceDate: e.price_date ?? e.price_source?.date,
    stale: e.price_stale ?? e.price_source?.stale, size: e.size ?? e.product.quantity, pack: e.pack_cents, ratio: e.size_ratio,
  });
  const os = r?.original?.score?.total;
  const listOf = (k: string) => (r?.rankings?.[k === 'match' ? 'quality' : k] ?? []).map(rowOf).filter((e: any) => {
    if (hidden.includes(e.product.id)) return false;
    if (k === 'closest') return true;                              // genuine substitutes, price or availability not required
    const q = os != null && e.product.score?.total != null ? e.product.score.total - os : null;
    if (k === 'budget') return e.price100 != null;                 // ordered by unit price: cheapest first
    if (k === 'match') return q == null || q >= 0;                 // equal or better quality
    return e.price100 != null;                                     // value: quality-price score
  });
  const shown = listOf(rk);
  const tabs = [
    { key: 'closest', label: t('rank.closest') },
    { key: 'budget', label: t('rank.budget') },
    ...(listOf('value').length > 0 ? [{ key: 'value', label: t('rank.value') }] : []),
    ...(listOf('match').length > 0 ? [{ key: 'match', label: t('rank.match') }] : []),
  ];
  useEffect(() => { if (r && !tabs.some((x) => x.key === rk)) setRk(tabs[0]?.key ?? 'closest'); }, [r, tabs.map((x) => x.key).join()]);
  const nothingNear = hasHome && !!r && ['budget', 'value', 'quality'].every((k) => !(r.rankings?.[k]?.length));

  // Only the difference against the scanned product is shown in the list (per kilo/litre, or per pack); real prices are in the details.
  const diffOf = (e: any): { text: string; tone: string; sub?: string } | null => {
    const o = r?.original_price;
    if (!o) return null;
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
      {r?.original_price ? <Segmented value={diffBy} onChange={(k) => setDiffBy(k as 'kg' | 'pack')} options={[{ key: 'kg', label: t('diff.byKg') }, { key: 'pack', label: t('diff.byPack') }]} /> : null}
      {r?.original_price?.per100_cents != null ? <Text style={{ color: c.ink, fontSize: 14, marginBottom: 6 }}>{t('diff.yours')} : <Text style={{ fontWeight: '700' }}>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</Text>{r.original_size?.amount ? ` · ${sizeLabel(r.original_size)}` : ''}{r.original_price.pack_cents != null ? ` · ${formatCents(r.original_price.pack_cents)}` : ''}</Text> : null}

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

      {r && !busy && shown.length > 0 ? (() => {
        const savedIds = useHistory.getState().saved.map((s) => s.id);
        const orig = useHistory.getState().productById(barcode ?? '') ?? (r.original ? { ...r.original, id: r.original.id ?? barcode } : null);
        const all = [orig, ...shown.map((e: any) => e.product)].filter(Boolean);
        const done = all.every((p: any) => savedIds.includes(p.id));
        return <Button small plain disabled={done} onPress={() => { hx.success(); useHistory.getState().saveMany(all); setNote(t('list.savedN', { n: all.length })); setTimeout(() => setNote(''), 2500); }}>{done ? t('list.allSaved') : t('list.saveAll', { n: all.length })}</Button>;
      })() : null}
      {r && !busy && rk === 'budget' && shown.length > 0 ? <Muted small>{t('alt.cheapestNote')}</Muted> : null}

      {r && !busy ? shown.map((e: any, i: number) => {
        const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
        const dif = diffOf(e);
        const why = [e.why && String(e.why).length <= 120 ? e.why : '', e.conf && !e.estimated && e.price100 != null ? t('alt.conf_' + e.conf) : ''].filter(Boolean).join(' · ');
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
                {r?.original?.score ? (() => { const dd = e.product.score.total - r.original.score.total; return <Text style={{ color: dd > 0 ? c.accent : dd < 0 ? c.bad : c.mut, fontWeight: '600', fontSize: 13 }}>{dd === 0 ? t('score.same') : `${dd > 0 ? '+' : '−'}${Math.abs(dd)} ${t('score.pts')}`}</Text>; })() : null}
              </View> : <View />}
              <View style={{ alignItems: 'flex-end' }}>
                {u ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700' }}>{formatCents(u.perUnitCents)}/{u.unit}{e.pack != null ? <Muted small> ({formatCents(e.pack)})</Muted> : null}</Text>
                  : e.pack != null ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700' }}>{formatCents(e.pack)}</Text> : null}
                {dif ? <Text style={{ color: dif.tone, fontWeight: '600', fontSize: 13 }}>{dif.text}</Text> : null}
              </View>
            </Row>
            {why ? <Muted small>{why}</Muted> : null}
            {e.avail && e.avail.state !== 'unknown' ? <View style={{ marginTop: 6 }}>
              <Pill tone={e.avail.state === 'observed_at_store' ? 'g' : 'w'}>
                {e.avail.state === 'observed_at_store' ? t('avail.observed', { s: e.avail.store ?? '?', d: e.avail.date ?? '' }) : e.avail.state === 'seen_at_chain' ? t('avail.chain') : t('avail.listed')}
              </Pill>
            </View> : null}
            {e.product.chains?.length > 0 ? <Row wrap style={{ marginTop: 8 }}>{e.product.chains.slice(0, 6).map((id: string) => <ChainBadge key={id} id={id} />)}{e.product.chains.length > 6 ? <Muted small>+{e.product.chains.length - 6}</Muted> : null}</Row> : null}
            <Button small plain onPress={() => { hx.light(); setDetail(e); }}>{t('simple.moreInfo')}</Button>
          </Card>);
      }) : null}

      <Sheet open={!!detail} onClose={() => setDetail(null)} title={detail?.product.name}>{detail ? detailBody(detail) : null}</Sheet>
      <Toast text={note} />
    </Screen>
  );
}
