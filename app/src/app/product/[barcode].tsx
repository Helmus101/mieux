import { useEffect, useRef, useState } from 'react';
import { Linking, Pressable, Text, View } from 'react-native';
import { Image } from 'expo-image';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { api } from '@shared/api/client';
import { additiveInfo } from '@shared/additives';
import { getStrict } from '@shared/config';
import { t } from '@shared/i18n';
import { formatCents, isLiquid } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { priceHeadline } from '@shared/verdict';
import { Bar, Body, Brand, Button, Card, Collapsible, H, Loader, Muted, NavBar, Group, Pill, Press, Row, Screen, ScoreTile, Sheet, Skeleton, haptic } from '@/components/ui';
import PqExplain from '@/components/PqExplain';
import SaveButton from '@/components/SaveButton';
import Where from '@/components/Where';
import { prefetchAlternatives } from '@/lib/alternatives';
import { readCache, writeCache } from '@/lib/cache';
import { toneColor, useTheme } from '@/lib/theme';

/* eslint-disable @typescript-eslint/no-explicit-any */
type Err = { kind: 'notfound' | 'notfood' | 'invalid' | 'server' | 'network' | 'rate' | 'auth'; msg: string };
const PRODUCT_CACHE_MS = 24 * 60 * 60_000, PRICE_WAIT_MS = 12000;
const num = (v: number) => String(Math.round(v * 10) / 10).replace('.', ',');
const zc = (x?: string | null) => (x === 'g2' || x === 'y' || x === 'w' || x === 'b' ? x : 'g');

const prodKey = (barcode: string, approximate: boolean) => {
  const p = useProfile.getState();
  return `prod:${barcode}:${approximate ? 1 : 0}:${getStrict() ? 1 : 0}:${p.diet ?? 'omnivore'}:${[...(p.allergens ?? [])].sort().join('+')}`;
};

const errKind = (e: any): Err => {
  const st = e?.response?.status, detail = e?.response?.data?.detail;
  const msg = typeof detail === 'string' ? detail : '';
  if (!e?.response) return { kind: 'network', msg };
  if (st === 404) return { kind: /food/i.test(msg) ? 'notfood' : 'notfound', msg };
  if (st === 400 || st === 422) return { kind: 'invalid', msg };
  if (st === 429) return { kind: 'rate', msg };
  if (st === 401 || st === 403) return { kind: 'auth', msg };
  return { kind: 'server', msg };
};

/** The barème: a track split into rating zones with a marker where this product sits. */
function ScaleBar({ scale }: { scale: any }) {
  const c = useTheme();
  const zones = (scale.zones ?? []) as any[], max = scale.max || zones[zones.length - 1]?.to || 1;
  const pos = Math.max(0, Math.min(1, scale.value / max)) * 100;
  return (
    <View style={{ gap: 4, marginTop: 4 }}>
      <View style={{ height: 8, flexDirection: 'row', borderRadius: 4, overflow: 'hidden' }}>
        {zones.map((z, i) => <View key={i} style={{ flex: Math.max(0.0001, z.to - z.from), backgroundColor: toneColor(zc(z.tone), c.dark) }} />)}
        <View style={{ position: 'absolute', left: `${pos}%`, top: -2, width: 3, height: 12, backgroundColor: c.ink, borderRadius: 2 }} />
      </View>
    </View>
  );
}

export default function ProductRoute() {
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  return <ProductView barcode={barcode} />;
}

/** The product page. As a route it reads the barcode from the URL; the scanner's result sheet renders the very same view in place. */
export function ProductView({ barcode }: { barcode?: string }) {
  const r = useRouter(), c = useTheme();
  const estimates = useProfile((s) => s.estimates), country = useProfile((s) => s.country);
  const addCompare = useProfile((s) => s.addCompare), removeCompare = useProfile((s) => s.removeCompare);
  const hist = useHistory();
  const [d, setD] = useState<any>(() => (barcode ? readCache(prodKey(barcode, estimates), PRODUCT_CACHE_MS) : null));
  const [err, setErr] = useState<Err | null>(null), [attempt, setAttempt] = useState(0), [sheet, setSheet] = useState<string | null>(null);
  const [webP, setWebP] = useState<any>(null);
  const [priceSettledFor, setSettled] = useState<string | null>(null), [gaveUpFor, setGaveUp] = useState<string | null>(null);
  const autoTries = useRef(0);

  useEffect(() => {
    if (!barcode) return;
    setD(readCache(prodKey(barcode, estimates), PRODUCT_CACHE_MS)); setErr(null);
    let cancelled = false, retry: ReturnType<typeof setTimeout> | undefined;
    api.getProduct(barcode, estimates)
      .then((x: any) => { if (cancelled) return; setD(x); writeCache(prodKey(barcode, estimates), x); hist.addScan(x.product); api.addScan(barcode).catch(() => undefined); })
      .catch((e: any) => {
        if (cancelled) return;
        const k = errKind(e);
        if (autoTries.current < 2 && (k.kind === 'server' || k.kind === 'network')) { autoTries.current += 1; retry = setTimeout(() => setAttempt((n) => n + 1), 1200); return; }
        // Offline: fall back to the copy kept on the device.
        const kept = useHistory.getState().productById(barcode);
        if (kept && k.kind === 'network') setD({ product: kept, fit: [], price_context: null, offline: true }); else setErr(k);
      });
    return () => { cancelled = true; if (retry) clearTimeout(retry); };
  }, [barcode, estimates, attempt]);
  useEffect(() => { autoTries.current = 0; }, [barcode]);
  useEffect(() => { if (barcode) prefetchAlternatives(barcode); }, [barcode]);

  const headKind = d ? priceHeadline(d.price_context).kind : null;
  useEffect(() => {   // no observed price: one search for an approximate web price
    let live = true, giveUp: ReturnType<typeof setTimeout> | undefined;
    setWebP(null);
    if (barcode && d && headKind === 'none') {
      giveUp = setTimeout(() => { if (live) setGaveUp(barcode); }, PRICE_WAIT_MS);
      api.getWebPriceQuick(barcode).then((w: any) => { if (live && w) setWebP(w); }).finally(() => { if (live) setSettled(barcode); });
    }
    return () => { live = false; if (giveUp) clearTimeout(giveUp); };
  }, [barcode, d?.product?.id, headKind]);
  const inCompare = useProfile((s) => !!d?.product && s.compare.includes(d.product.id));

  if (err) return (
    <Screen>
      <NavBar />
      <Card>
        <H style={{ fontSize: 22 }}>{t(err.kind === 'rate' ? 'product.nf.rateTitle' : err.kind === 'auth' ? 'product.nf.authTitle' : err.kind === 'notfood' ? 'product.nf.foodTitle' : err.kind === 'notfound' ? 'product.nf.title' : err.kind === 'invalid' ? 'product.nf.invalidTitle' : err.kind === 'network' ? 'product.nf.netTitle' : 'product.nf.srvTitle')}</H>
        {err.kind === 'notfound' && <><Muted>{t('product.nf.code', { c: barcode ?? '' })}</Muted><Muted small>{t('product.nf.why')}</Muted></>}
        {err.kind === 'notfood' && <Muted>{t('product.nf.food')}</Muted>}
        {err.kind === 'rate' && <Muted>{t('product.nf.rate')}</Muted>}
        {err.kind === 'auth' && <Muted>{t('product.nf.auth')}</Muted>}
        {err.kind === 'invalid' && <Muted>{t('product.nf.invalid', { c: barcode ?? '' })}</Muted>}
        {err.kind === 'network' && <Muted>{t('net.down')}</Muted>}
        {err.kind === 'server' && <Muted>{t('product.nf.srv')}</Muted>}
      </Card>
      <Button primary onPress={() => { autoTries.current = 0; setAttempt((n) => n + 1); }}>{t('common.retry')}</Button>
      <Button onPress={() => r.replace('/scan')}>{t('product.nf.scanAgain')}</Button>
    </Screen>
  );
  if (!d) return (
    <Screen>
      <NavBar />
      <Row><Skeleton h={96} w={96} /><View style={{ flex: 1, gap: 8 }}><Skeleton h={14} w="40%" /><Skeleton h={22} w="85%" /><Skeleton h={22} w="60%" /></View></Row>
      <Loader steps={t('common.stepsProduct').split('|')} onRetry={() => setAttempt((n) => n + 1)} />
    </Screen>
  );

  const p = d.product, pc = d.price_context, head = priceHeadline(pc);
  const pricePending = head.kind === 'none' && !d.offline && priceSettledFor !== barcode && gaveUpFor !== barcode;
  const webPerKg = webP?.per100_cents > 0 ? Math.round(webP.per100_cents * 10) : null;
  const perUnit = (isLiquid(p) ? 'simple.perL' : 'simple.perKg');
  const info = sheet ? additiveInfo(sheet) : null;
  const sItem = sheet ? ((p.score?.additives?.items ?? []) as any[]).find((x) => x.code === sheet) : null;

  // Allergen / diet verdict
  const rf = (d.fit ?? []).filter((x: any) => x.priority.startsWith('allergen:') || x.priority.startsWith('diet:'));
  const key = (x: any) => x.priority.split(':')[1];
  const nm = (x: any) => t((x.priority.startsWith('allergen:') ? 'restr.a_' : 'restr.d_') + key(x));
  const has = rf.filter((x: any) => x.priority.startsWith('allergen:') && x.status === 'conflict' && p.allergens.includes(key(x))).map(nm);
  const tr2 = rf.filter((x: any) => x.priority.startsWith('allergen:') && x.status === 'conflict' && !p.allergens.includes(key(x))).map(nm);
  const dietBad = rf.filter((x: any) => x.priority.startsWith('diet:') && x.status === 'conflict').map(nm);
  const unk = rf.filter((x: any) => x.status === 'unknown').map(nm);
  const lines = [has.length ? t('restr.contains', { x: has.join(', ') }) : '', tr2.length ? t('restr.traces', { x: tr2.join(', ') }) : '', ...dietBad.map((x: string) => t('restr.notDiet', { x })), unk.length ? t('restr.unknown', { x: unk.join(', ') }) : ''].filter(Boolean);
  const bad = has.length + tr2.length + dietBad.length > 0;

  const s = p.score;
  const dims = ((s?.dimensions ?? []) as any[]).filter((x) => x.relevant !== false && x.key !== 'micro' && !x.missing && x.score != null);
  const allAdd = [...(s?.additives?.items ?? [])] as any[];
  const adds = allAdd.filter((x) => x.known || !allAdd.some((o) => o !== x && x.code.startsWith(o.code))).sort((x, y) => y.level.localeCompare(x.level) || x.code.localeCompare(y.code));
  const risky = adds.filter((x) => x.level === 'C' || x.level === 'D');
  const raw = String(p.ingredientsText || '').trim();
  const m = raw.match(/\s*(?:traces?(?:\s+[ée]ventuelles?)?|peut\s+contenir|may\s+contain)\b[\s:]*(?:de\s+|d['’]\s*|du\s+|des\s+|of\s+)?/i);
  const ing = (m && m.index != null ? raw.slice(0, m.index) : raw).replace(/[.\s]+$/, ''), traces = m && m.index != null ? raw.slice(m.index + m[0].length).replace(/[.\s]+$/, '') : '';
  const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
  const n = p.nutriments;
  const nutRows: [string, number | null | undefined, string, boolean?][] = n ? [['energy', n.energyKcal100g, 'kcal'], ['fat', n.fat100g, 'g'], ['sat', n.saturatedFat100g, 'g', true], ['carbs', n.carbohydrates100g, 'g'], ['sugars', n.sugars100g, 'g', true], ['fibre', n.fiber100g, 'g'], ['protein', n.protein100g, 'g'], ['salt', n.salt100g, 'g']] : [];

  return (
    <Screen>
      <NavBar title={p.name} right={<SaveButton product={p} />} />
      {d.offline && <Pill tone="w">{t('history.offline')}</Pill>}
      {p.soldInFrance !== true && !d.offline && <Card><Pill tone="w">{p.soldInFrance === false ? t(country === 'US' ? 'simple.notUs' : 'simple.notFr') : t(country === 'US' ? 'simple.usUnknown' : 'simple.frUnknown')}</Pill></Card>}

      {rf.length > 0 && <Card>
        <Row style={{ alignItems: 'flex-start' }}>
          <Text style={{ fontSize: 22, color: bad ? c.bad : lines.length ? c.warn : c.accent }}>{bad ? '✗' : lines.length ? '!' : '✓'}</Text>
          <View style={{ flex: 1, gap: 4 }}>
            {lines.length ? lines.map((l) => <Body key={l} bold style={{ color: bad ? c.bad : c.ink }}>{l}</Body>) : <Body bold>{t('restr.ok')}</Body>}
            <Muted small>{t('restr.check')}</Muted>
          </View>
        </Row>
      </Card>}

      <Row style={{ alignItems: 'flex-start', gap: 14 }}>
        {p.imageUrl ? <Image source={{ uri: p.imageUrl }} style={{ width: 96, height: 96, borderRadius: 12, backgroundColor: '#fff' }} contentFit="contain" priority="high" /> : null}
        <View style={{ flex: 1, gap: 2 }}>
          {p.brand && p.brand.toLowerCase() !== (p.name || '').toLowerCase() && <Muted small>{p.brand}</Muted>}
          <Text style={{ color: c.ink, fontSize: 22, fontWeight: '700' }}>{p.name}</Text>
          {p.quantityText ? <Muted small>{p.quantityText}</Muted> : null}
        </View>
      </Row>

      {head.kind !== 'none'
        ? <Row wrap><Body bold>{t(perUnit, { p: formatCents(head.perKgCents!) })}</Body>{head.kind === 'estimate' && <Pill tone="w">{t('est.pill')}</Pill>}</Row>
        : webPerKg != null ? <Row wrap><Body bold>~ {t(perUnit, { p: formatCents(webPerKg) })}</Body><Pill tone="w">{t('est.pill')}</Pill></Row> : null}

      {s && pricePending ? <Row><Skeleton h={64} w={110} /><Skeleton h={64} w={110} /></Row> : s ? <Card style={{ gap: 12 }}>
        <Row style={{ alignItems: 'flex-start', gap: 28 }}>
          <View style={{ gap: 2 }}><Muted small>{t('score.quality')}</Muted><ScoreTile value={s.total} tone={s.tone === 'b' ? 'b' : s.tone === 'w' ? 'w' : 'g'} /><Body bold>{t('score.' + s.band)}</Body></View>
          {pc?.value && <View style={{ gap: 2 }}><Row style={{ gap: 0 }}><Muted small>{t('score.value')}</Muted><PqExplain /></Row><ScoreTile value={pc.value.value_score} tone={pc.value.value_score >= 65 ? 'g' : pc.value.value_score >= 40 ? 'w' : 'b'} /><Body bold>{pc.value.value_score >= 65 ? t('score.good') : pc.value.value_score >= 40 ? t('score.average') : t('score.poor')}</Body></View>}
        </Row>
        <View style={{ gap: 4 }}>
          {(s.flags ?? []).slice(0, 3).map((f: any) => <Text key={f.key} style={{ color: f.level === 'bad' ? c.bad : c.warn, fontWeight: '600', fontSize: 15 }}>• {t('flag.' + f.key)}</Text>)}
          {risky.slice(0, 3).map((x) => <Pressable key={x.code} onPress={() => { haptic('select'); setSheet(x.code); }}><Text style={{ color: x.level === 'D' ? c.bad : c.warn, fontWeight: '600', fontSize: 15 }}>• {x.code.toUpperCase()}{x.name ? ' · ' + x.name.split(' (')[0] : ''}</Text></Pressable>)}
          {s.incomplete && <Muted>• {t('sdim.incomplete')}</Muted>}
        </View>
      </Card> : <Muted>{t('score.na')}</Muted>}

      <Press feedback="heavy" onPress={() => r.push(`/alternatives/${p.id}`)} style={{ backgroundColor: c.accent, borderRadius: 12, paddingVertical: 18, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flex: 1 }}><Text style={{ color: c.accentInk, fontWeight: '700', fontSize: 17 }}>{t('simple.findBetter')}</Text><Text style={{ color: c.accentInk, opacity: 0.85 }}>{t('simple.findBetterSub')}</Text></View>
        <Text style={{ color: c.accentInk, fontSize: 26 }}>→</Text>
      </Press>

      <Group>
      {s && <Collapsible title={`${t('sdim.title')} · ${s.total}${t('score.outOf')}`}>
        <Muted small>{t('sdim.profile', { x: t('prof.' + s.profile) })}{s.confidence ? ' · ' + t('sdim.confidence', { x: t('sdim.conf_' + s.confidence.level), p: s.confidence.pct }) : ''}</Muted>
        {((s.parts ?? []) as any[]).map((x) => <View key={x.key} style={{ gap: 4, marginVertical: 6 }}><Row spread><Body bold>{t('score.part_' + x.key)}</Body><Muted>{num(x.got)} / {x.of} {t('score.pts')}</Muted></Row><Bar value={x.of ? x.got / x.of : 0} tone={x.of && x.got / x.of >= 0.8 ? 'g' : x.of && x.got / x.of >= 0.6 ? 'g2' : x.of && x.got / x.of >= 0.4 ? 'w' : 'b'} /></View>)}
        <H style={{ marginTop: 10 }}>{t('sdim.nutritional')}</H>
        {dims.filter((x) => x.group === 'nutrition').map((x) => <View key={x.key} style={{ gap: 4, marginVertical: 6 }}>
          <Row spread><Body>{t('sdim.' + x.key)}{x.scale?.estimated ? ' *' : ''}</Body><Text style={{ color: toneColor(zc(x.scale?.tone ?? x.tone), c.dark), fontWeight: '700' }}>{x.scale ? `${num(x.scale.value)} ${x.scale.unit}` : ''}{x.scale?.tier ? ' · ' + t('tier.' + x.scale.tier) : ''}</Text></Row>
          {x.scale?.zones?.length ? <ScaleBar scale={x.scale} /> : <Bar value={x.score / 100} tone={zc(x.tone)} />}
          {x.key === 'fat' && x.detail?.sat != null && <Muted small>{t('sdim.fatDetail', { s: num(x.detail.sat), f: num(x.detail.total ?? 0) })}</Muted>}
        </View>)}
        <H style={{ marginTop: 10 }}>{t('sdim.ingredient')}</H>
        {dims.filter((x) => x.group === 'ingredients').map((x) => <View key={x.key} style={{ gap: 4, marginVertical: 6 }}><Row spread><Body>{t('sdim.' + x.key)}</Body><Text style={{ color: toneColor(zc(x.tone), c.dark), fontWeight: '700' }}>{x.score}/100</Text></Row><Bar value={x.score / 100} tone={zc(x.tone)} /></View>)}
        <Muted small>{t('score.indicative')}</Muted>
      </Collapsible>}

      {n && <Collapsible title={t('product.nutrition')}>
        {nutRows.map(([k, v, u, sub]) => <Row key={k} spread><Body style={{ paddingLeft: sub ? 14 : 0, opacity: sub ? 0.7 : 1 }}>{t('product.' + k)}</Body><Body bold>{v == null ? '–' : `${num(v)} ${u}`}</Body></Row>)}
        <Muted small>{t('product.nutriNote')}</Muted>
      </Collapsible>}

      {adds.length > 0 && <Collapsible title={`${t('addl.title')} · ${t('addl.count', { n: adds.length })}${risky.length ? ' · ' + t('addl.bad', { n: risky.length }) : ''}`}>
        {adds.map((a) => (
          <Pressable key={a.code} onPress={() => { haptic(); setSheet(a.code); }} style={{ paddingVertical: 6, gap: 2 }}>
            <Row><View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: a.level === 'D' ? c.bad : a.level === 'C' ? c.warn : c.accent }} /><Body bold>{a.code.toUpperCase()}</Body><Muted style={{ flex: 1 }}>{a.name || additiveInfo(a.code)?.name || ''}</Muted><Muted>›</Muted></Row>
            {(a.level === 'C' || a.level === 'D') && a.note ? <Muted small>{a.note}</Muted> : null}
          </Pressable>
        ))}
      </Collapsible>}

      <Collapsible title={t('where.title')}><Where barcode={p.id} liquid={isLiquid(p)} /></Collapsible>

      {p.micronutrients?.length > 0 && <Collapsible title={t('simple.microSec')}>
        {p.micronutrients.map((x: any) => <View key={x.key} style={{ gap: 4, marginVertical: 6 }}><Row spread><Body>{t('micro.' + x.key)}</Body><Muted>{x.amount} {x.unit} · {x.nrv_pct}%</Muted></Row><Bar value={Math.min(1, x.nrv_pct / 100)} /></View>)}
        <Muted small>{t('micro.note')}</Muted>
      </Collapsible>}

      <Collapsible title={t('simple.ingSec')}>
        <H>{t('ing.list')}</H>
        <Body>{ing ? cap(ing) + '.' : t('product.noIng')}</Body>
        {p.allergens.length > 0 && <><H style={{ marginTop: 8 }}>{t('ing.allergens')}</H><Body style={{ color: c.bad }}>{p.allergens.map((a: string) => { const k = 'restr.a_' + a.replace(/^en:/, ''), v = t(k); return v === k ? a : v; }).join(', ')}</Body></>}
        {p.allergens.length === 0 && <Muted small>{raw ? t('product.allergenNone') : t('product.allergenMissing')}</Muted>}
        {traces ? <><H style={{ marginTop: 8 }}>{t('ing.traces')}</H><Body>{cap(traces) + '.'}</Body></> : null}
        <Pressable onPress={() => Linking.openURL(`https://world.openfoodfacts.org/product/${p.id}`)}><Body style={{ color: c.accent, marginTop: 8 }}>{t('product.correct')}</Body></Pressable>
      </Collapsible>
      </Group>

      <Button onPress={() => { if (inCompare) removeCompare(p.id); else { addCompare(p.id); r.push('/compare'); } }}>{inCompare ? t('compare.remove') : t('product.compare')}</Button>
      <View style={{ alignItems: 'center', gap: 2, marginTop: 8 }}><Brand size={18} /><Muted small>{t('brand.tagline')}</Muted></View>

      <Sheet open={!!sheet} onClose={() => setSheet(null)} title={sheet ? sheet.toUpperCase() + (info ? ' · ' + info.name : sItem?.name ? ' · ' + sItem.name : '') : ''}>
        {sItem?.use ? <><H>{t('add.use')}</H><Body>{sItem.use}</Body></> : null}
        {sItem?.found ? <><H>{t('add.found')}</H><Body>{sItem.found}</Body></> : null}
        {info ? <>
          {!sItem?.use && <><H>{t('add.why')}</H><Body>{info.why}</Body></>}
          <H>{t('add.evidence')}</H><Body>{info.evidence}</Body>
          <H>{t('add.regulation')}</H><Body>{info.regulation}</Body>
          <H>{t('add.advice')}</H><Body>{info.advice}</Body>
          <Pressable onPress={() => Linking.openURL(info.source)}><Body style={{ color: c.accent }}>{t('add.source')} : EFSA / UE</Body></Pressable>
        </> : sItem?.known ? <>
          <Pill tone={sItem.level === 'D' ? 'b' : sItem.level === 'C' ? 'w' : 'g'}>{t('addl.' + sItem.level)}</Pill>
          {sItem.note ? <><H>{t('add.health')}</H><Body>{sItem.note}</Body></> : null}
        </> : <Muted>{t('add.unknown')}</Muted>}
        <Pressable onPress={() => Linking.openURL('https://food.ec.europa.eu/food-safety/food-improvement-agents/additives/database_en')}><Body style={{ color: c.accent }}>{t('add.euDb')}</Body></Pressable>
        <Button onPress={() => setSheet(null)}>{t('common.done')}</Button>
      </Sheet>
    </Screen>
  );
}
