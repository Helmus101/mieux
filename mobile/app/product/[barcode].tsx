import { useEffect, useRef, useState } from 'react';
import { Image, Linking, Pressable, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { api } from '@shared/api/client';
import { additiveInfo } from '@shared/additives';
import { t } from '@shared/i18n';
import { formatCents, isLiquid } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { priceHeadline } from '@shared/verdict';
import { AmountScale, Bar, Button, Card, Collapsible, Loader, Muted, NavBar, NovaBadge, NutriScore, Pill, Row, Screen, ScoreBar, Segmented, Sheet, Skeleton, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import SaveButton from '../../src/SaveButton';
import KnowCard from '../../src/KnowCard';
import Where from '../../src/Where';
import * as hx from '../../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const TONE_V: Record<string, string> = { g: '#1F4D3A', g2: '#9CBE77', y: '#D95A22', w: '#D95A22', b: '#A33B2B' };
const toneVar = (tn?: string) => TONE_V[tn ?? ''] ?? '#0F1A15';

type ErrKind = 'notfound' | 'notfood' | 'invalid' | 'server' | 'network' | 'rate' | 'auth';

/** Product sheet: the same blocks, in the same order, as the web screen. */
export default function Product() {
  const c = useTheme();
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const { go, back } = useNav();
  const estimates = useProfile((s) => s.estimates), addCompare = useProfile((s) => s.addCompare), country = useProfile((s) => s.country);
  const hist = useHistory();
  const [d, setD] = useState<any>(null), [err, setErr] = useState<{ kind: ErrKind; msg: string } | null>(null);
  const [attempt, setAttempt] = useState(0), [offline, setOffline] = useState(false), [sheet, setSheet] = useState<string | null>(null);
  const [basis, setBasis] = useState<'100' | 'serving' | 'pack'>('100');
  const autoTries = useRef(0);

  useEffect(() => {
    if (!barcode) return;
    setD(null); setErr(null); setOffline(false);
    let cancelled = false, retryTimer: ReturnType<typeof setTimeout> | undefined;
    api.getProduct(barcode, estimates).then((x: any) => { setD(x); hist.addScan(x.product); api.addScan(barcode).catch(() => undefined); })
      .catch((e: any) => {
        if (!cancelled && autoTries.current < 2 && e?.response?.status !== 400 && !(e?.response && ![404, 502, 503, 504].includes(e.response.status))) {
          autoTries.current += 1; retryTimer = setTimeout(() => setAttempt((n) => n + 1), 1200); return;
        }
        const snap = useHistory.getState().productById(barcode);
        if (snap && e?.response?.status !== 404) { setD({ product: snap, fit: [], price_context: null }); setOffline(true); return; }
        const st = e?.response?.status;
        setErr({
          kind: st === 404 ? (e.response.data?.detail === 'not_food' ? 'notfood' : 'notfound') : st === 400 ? 'invalid' : st === 429 ? 'rate' : st === 401 ? 'auth'
            : e?.response ? 'server' : 'network',
          msg: st ? `HTTP ${st}${typeof e.response?.data?.detail === 'string' ? ' · ' + e.response.data.detail : ''}` : (e?.message ?? ''),
        });
      });
    return () => { cancelled = true; if (retryTimer) clearTimeout(retryTimer); };
  }, [barcode, estimates, attempt]);
  useEffect(() => { autoTries.current = 0; }, [barcode]);

  if (err) {
    const titleKey = err.kind === 'rate' ? 'product.nf.rateTitle' : err.kind === 'auth' ? 'product.nf.authTitle' : err.kind === 'notfood' ? 'product.nf.foodTitle'
      : err.kind === 'notfound' ? 'product.nf.title' : err.kind === 'invalid' ? 'product.nf.invalidTitle' : err.kind === 'network' ? 'product.nf.netTitle' : 'product.nf.srvTitle';
    const retryable = err.kind === 'server' || err.kind === 'network' || err.kind === 'rate' || err.kind === 'auth';
    return (
      <Screen>
        <NavBar onBack={back} />
        <Card>
          <Text style={{ color: c.ink, fontSize: 22, fontWeight: '700', marginBottom: 6 }}>{t(titleKey)}</Text>
          {err.kind === 'notfound' ? <><Text style={{ color: c.ink, marginVertical: 4 }}>{t('product.nf.code', { c: barcode ?? '' })}</Text><Muted small>{t('product.nf.why')}</Muted></> : null}
          {err.kind === 'notfood' ? <Muted>{t('product.nf.food')}</Muted> : null}
          {err.kind === 'rate' ? <Muted>{t('product.nf.rate')}</Muted> : null}
          {err.kind === 'auth' ? <Muted>{t('product.nf.auth')}</Muted> : null}
          {err.kind === 'invalid' ? <Muted>{t('product.nf.invalid', { c: barcode ?? '' })}</Muted> : null}
          {err.kind === 'network' ? <Muted>{t('net.down')}</Muted> : null}
          {err.kind === 'server' ? <Muted>{t('product.nf.srv')}</Muted> : null}
          {err.msg && (err.kind === 'server' || err.kind === 'auth') ? <Muted small>{err.msg}</Muted> : null}
        </Card>
        {retryable ? <Button primary onPress={() => setAttempt((n) => n + 1)}>{t('common.retry')}</Button> : null}
        <Button primary={!retryable} onPress={() => go(routes.scan)}>{t('product.nf.scanAgain')}</Button>
        {err.kind === 'notfound' ? <Button plain onPress={() => setAttempt((n) => n + 1)}>{t('common.retry')}</Button> : null}
      </Screen>
    );
  }
  if (!d) return <Screen><NavBar onBack={back} /><Loader steps={t('common.stepsProduct').split('|')} onRetry={() => setAttempt((n) => n + 1)} /><Skeleton h={90} /><Skeleton h={120} /></Screen>;

  const p = d.product, pc = d.price_context;
  const liquid = isLiquid(p), per = liquid ? 'ml' : 'g';
  const bases = [{ key: '100', label: t('sdim.per100', { u: per }), f: 1 },
    ...(p.servingG ? [{ key: 'serving', label: t('sdim.perServing', { n: Math.round(p.servingG), u: per }), f: p.servingG / 100 }] : []),
    ...(p.quantity?.amount ? [{ key: 'pack', label: t('sdim.perPack', { n: Math.round(p.quantity.amount), u: per }), f: p.quantity.amount / 100 }] : [])];
  const factor = (bases.find((b) => b.key === basis) ?? bases[0]).f;
  const amt = (v: number | null | undefined) => (v == null ? '—' : String(Math.round(v * factor * 10) / 10).replace('.', ','));
  const head = priceHeadline(pc);
  const info = sheet ? additiveInfo(sheet) : null;
  const sItem = sheet ? (((p.score?.additives?.items ?? []) as any[]).find((x) => x.code === sheet) ?? null) : null;

  const fit = (d.fit ?? []) as any[];
  const rf = fit.filter((x) => x.priority.startsWith('allergen:') || x.priority.startsWith('diet:'));
  const key = (x: any) => x.priority.split(':')[1];
  const nm = (x: any) => t((x.priority.startsWith('allergen:') ? 'restr.a_' : 'restr.d_') + key(x));
  const has = rf.filter((x) => x.priority.startsWith('allergen:') && x.status === 'conflict' && p.allergens.includes(key(x))).map(nm);
  const tr2 = rf.filter((x) => x.priority.startsWith('allergen:') && x.status === 'conflict' && !p.allergens.includes(key(x))).map(nm);
  const dietBad = rf.filter((x) => x.priority.startsWith('diet:') && x.status === 'conflict').map(nm);
  const unk = rf.filter((x) => x.status === 'unknown').map(nm);
  const lines = [has.length ? t('restr.contains', { x: has.join(', ') }) : '', tr2.length ? t('restr.traces', { x: tr2.join(', ') }) : '',
    ...dietBad.map((x: string) => t('restr.notDiet', { x })), unk.length ? t('restr.unknown', { x: unk.join(', ') }) : ''].filter(Boolean);
  const badFit = has.length + tr2.length + dietBad.length > 0;

  return (
    <Screen>
      <NavBar onBack={back} title={p.name} right={<SaveButton product={p} />} />
      {offline ? <Pill tone="w">{t('history.offline')}</Pill> : null}
      {p.soldInFrance !== true ? <Card><Pill tone="w">{p.soldInFrance === false ? t(country === 'US' ? 'simple.notUs' : 'simple.notFr') : t(country === 'US' ? 'simple.usUnknown' : 'simple.frUnknown')}</Pill></Card> : null}

      {rf.length ? <Card>
        <Row>
          <Text style={{ fontSize: 22, color: badFit ? c.bad : lines.length ? c.warn : c.accent }}>{badFit ? '✗' : lines.length ? '!' : '✓'}</Text>
          <View style={{ flex: 1 }}>
            {lines.length ? lines.map((l: string) => <Text key={l} style={{ color: badFit ? c.bad : c.ink, fontWeight: '600', marginBottom: 4 }}>{l}</Text>)
              : <Text style={{ color: c.ink, fontWeight: '600', marginBottom: 4 }}>{t('restr.ok')}</Text>}
            <Muted small>{t('restr.check')}</Muted>
          </View>
        </Row>
      </Card> : null}

      <Card>
        <Row>
          {p.imageUrl ? <Image source={{ uri: p.imageUrl }} style={{ width: 100, height: 100, borderRadius: 16, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
          <View style={{ flex: 1 }}><Muted>{p.brand}</Muted><Text style={{ color: c.ink, fontSize: 25, fontWeight: '800', letterSpacing: -0.5 }}>{p.name}</Text><Muted>{p.quantityText}</Muted></View>
        </Row>
        {p.score ? <>
          <View style={{ flexDirection: 'row', gap: 12, marginTop: 8 }}>
            <View style={{ flex: 1, backgroundColor: c.tint, borderRadius: 14, padding: 12 }}>
              <Muted small>{t('score.title')}</Muted>
              <Text style={{ color: p.score.tone === 'b' ? c.bad : p.score.tone === 'w' ? c.warn : c.accent, fontSize: 40, fontWeight: '800' }}>{p.score.total}<Text style={{ fontSize: 14, color: c.mut }}>{t('score.outOf')}</Text></Text>
              <Text style={{ color: c.ink, fontWeight: '700' }}>{t('score.' + p.score.band)}</Text>
            </View>
            <View style={{ flex: 1, backgroundColor: c.tint, borderRadius: 14, padding: 12 }}>
              <Muted small>{t('score.pq')}</Muted>
              {pc?.value ? <>
                <Text style={{ color: pc.value.value_score >= 65 ? c.accent : pc.value.value_score >= 40 ? c.warn : c.bad, fontSize: 40, fontWeight: '800' }}>{pc.value.value_score}<Text style={{ fontSize: 14, color: c.mut }}>{t('score.outOf')}</Text></Text>
                <Text style={{ color: c.ink, fontWeight: '700' }}>{pc.value.value_score >= 65 ? t('score.pqGood') : pc.value.value_score >= 40 ? t('score.pqOk') : t('score.pqLow')}</Text>
              </> : <>
                <Text style={{ color: c.mut, fontSize: 40, fontWeight: '800' }}>–</Text>
                <Text style={{ color: c.mut, fontWeight: '700' }}>{t('score.pqNone')}</Text>
              </>}
            </View>
          </View>
          <ScoreBar total={p.score.total} />
          <Muted small>{t('score.indicative')}</Muted>
          {(p.score.additives?.items ?? []).some((x: any) => x.level === 'C' || x.level === 'D') ? <Row wrap style={{ marginTop: 8 }}>
            {(p.score.additives.items as any[]).filter((x) => x.level === 'C' || x.level === 'D').slice(0, 4).map((x) => (
              <Pressable key={x.code} onPress={() => setSheet(x.code)}><Pill tone={x.level === 'D' ? 'b' : 'w'}>{x.code.toUpperCase()}{x.name ? ' · ' + x.name.split(' (')[0] : ''}</Pill></Pressable>
            ))}
          </Row> : null}
          {p.score.incomplete ? <Row style={{ marginTop: 6 }}><Pill>{t('sdim.incomplete')}</Pill></Row> : null}
          {p.score.flags?.length > 0 ? <Row wrap style={{ marginTop: 6 }}>{p.score.flags.slice(0, 3).map((f: any) => <Pill key={f.key} tone={f.level === 'bad' ? 'b' : 'w'}>{t('flag.' + f.key)}</Pill>)}</Row> : null}
        </> : <Muted>{t('score.na')}</Muted>}
        {head.kind !== 'none' ? <Row wrap style={{ marginTop: 10 }}>
          <Text style={{ color: c.ink, fontWeight: '700' }}>{head.kind === 'estimate' ? '~ ' : ''}{t(liquid ? 'simple.perL' : 'simple.perKg', { p: formatCents(head.perKgCents!) })}</Text>
          {head.kind === 'estimate' ? <Pill tone="w">{t('est.pill')}</Pill> : null}
        </Row> : <Muted small>{t('simple.noPrice')}</Muted>}
      </Card>

      <KnowCard p={p} />

      <Pressable onPress={() => { hx.light(); go(routes.alternatives(p.id)); }} style={({ pressed }) => ({ backgroundColor: c.tint, borderRadius: 18, padding: 16, marginVertical: 8, opacity: pressed ? 0.85 : 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' })}>
        <View><Text style={{ color: c.ink, fontWeight: '700', fontSize: 17 }}>{t('simple.findBetter')}</Text><Muted small>{t('simple.findBetterSub')}</Muted></View>
        <Text style={{ color: c.accent, fontSize: 22 }}>→</Text>
      </Pressable>


      {p.score ? <Collapsible title={t('sdim.title')}>
        {p.score.parts ? <Muted small>{p.score.parts.map((x: any) => `${t('score.part_' + x.key)} ${Math.round(x.got)}/${x.of}`).join(' · ')}{p.score.uncapped > p.score.total ? ` · ${t('score.cappedFrom', { a: p.score.uncapped, b: p.score.total })}` : ''}</Muted> : null}
        <View style={{ marginVertical: 8 }}><NutriScore grade={p.nutriScore} /></View>
        <Muted small>{t('sdim.profile', { x: t('prof.' + p.score.profile) })} · {t('sdim.confidence', { x: t('sdim.conf_' + p.score.confidence.level), p: p.score.confidence.pct })}{p.score.incomplete ? ' · ' + t('sdim.incomplete') : ''}</Muted>
        <Text style={{ color: c.mut, fontSize: 12, fontWeight: '600', marginTop: 12 }}>{t('sdim.amountsFor')}</Text>
        {bases.length > 1 ? <Segmented value={basis} onChange={(k) => setBasis(k as any)} options={bases.map((b) => ({ key: b.key, label: b.label }))} /> : <Muted small>{bases[0].label}</Muted>}
        <Row spread style={{ marginVertical: 10 }}>
          <View><Muted small>{t('sdim.nutritional')}</Muted><Text style={{ color: toneVar(p.score.nutritional.tone), fontWeight: '700', fontSize: 20 }}>{p.score.nutritional.score}</Text></View>
          <View><Muted small>{t('sdim.ingredient')}</Muted><Text style={{ color: toneVar(p.score.ingredient?.tone), fontWeight: '700', fontSize: 20 }}>{p.score.ingredient ? p.score.ingredient.score : '—'}</Text></View>
          <View><Muted small>{t('sdim.processing')}</Muted><NovaBadge group={p.novaGroup} estimated={p.novaEstimated} /></View>
        </Row>
        {p.score.caps?.length > 0 ? <Muted small>{p.score.caps.map((x: string) => t('cap.' + x)).join(' ')}</Muted> : null}
        <Text style={{ color: c.mut, fontSize: 12, fontWeight: '600', marginTop: 12 }}>{t('sdim.grp_nutrition')}</Text>
        {(p.score.dimensions as any[]).filter((x) => x.group === 'nutrition' && x.relevant && !x.missing).map((dim) => {
          const sg = dim.key === 'sugar' ? p.score.sugar : null, sk = sg?.kind;
          return (
            <View key={dim.key} style={{ marginVertical: 8 }}>
              <Row spread>
                <Text style={{ color: c.ink, flexShrink: 1 }}>{t('sdim.' + dim.key)}{sk === 'natural' ? <Text style={{ color: c.accent, fontSize: 12 }}> · {t('nut.sugarNatural')}</Text> : null}{(sk === 'added' || sk === 'mixed') ? <Text style={{ color: c.warn, fontSize: 12 }}> · {t('nut.sugarAdded')}</Text> : null}</Text>
                {dim.scale ? <Text style={{ color: c.ink }}><Text style={{ fontWeight: '700' }}>{dim.key === 'plant' ? dim.scale.value : amt(dim.scale.value)} {dim.scale.unit}</Text>{dim.scale.estimated ? <Muted small> ({t('add2.est')})</Muted> : null} <Text style={{ color: toneVar(dim.scale.tone), fontSize: 13 }}>{t((dim.scale.better === 'more' ? 'tierPos.' : 'tier.') + dim.scale.tier)}</Text></Text>
                  : <Text style={{ color: toneVar(dim.tone), fontSize: 13 }}>{dim.key === 'micro' ? t('sdim.microList', { n: (dim.detail?.rich?.length ?? 0) + (dim.detail?.source?.length ?? 0) }) : t('tier.' + (dim.score >= 75 ? 'excellent' : dim.score >= 50 ? 'good' : dim.score >= 25 ? 'poor' : 'bad'))}</Text>}
              </Row>
              {dim.scale ? <AmountScale scale={dim.scale} /> : null}
              {sg && (sk === 'added' || sk === 'mixed') && sg.added?.length > 0 ? <Muted small>{t('nut.sugarAddedNote', { x: sg.added.join(', ') })}</Muted> : null}
              {dim.key === 'fat' && dim.detail?.sat != null ? <Muted small>{t('sdim.fatDetail', { s: amt(dim.detail.sat), f: amt(dim.detail.total) })}{dim.detail.trans != null ? ' · ' + t('sdim.trans', { x: amt(dim.detail.trans) }) : ''}</Muted> : null}
            </View>);
        })}
        <Muted small>{t(p.score.mode === 'strict' ? 'score.method3' : 'score.method2')}</Muted>
      </Collapsible> : null}

      {p.score ? (() => {
        const all = [...(p.score.additives?.items ?? [])] as any[];
        const items = all.filter((x) => x.known || !all.some((o) => o !== x && x.code.startsWith(o.code))).sort((x, y) => y.level.localeCompare(x.level) || x.code.localeCompare(y.code));
        const risky = items.filter((x) => x.level === 'C' || x.level === 'D');
        return <Collapsible title={`${t('addl.title')} · ${items.length ? t('addl.count', { n: items.length }) + (risky.length ? ' · ' + t('addl.bad', { n: risky.length }) : '') : t('addl.none')}`}>
          {items.length === 0 ? <Muted>{t('addl.none')}</Muted> : null}
          {items.map((a) => {
            const hi = a.level === 'C' || a.level === 'D';
            const name = a.name || additiveInfo(a.code)?.name || '';
            return <Pressable key={a.code} onPress={() => { hx.light(); setSheet(a.code); }} style={{ paddingVertical: 8, borderTopWidth: 1, borderTopColor: c.line }}>
              <Row spread>
                <Row><View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: a.level === 'D' ? c.bad : a.level === 'C' ? c.warn : c.accent }} />
                  <Text style={{ color: c.ink, fontWeight: '700' }}>{a.code.toUpperCase()}</Text><Muted small>{name}</Muted></Row>
                <Text style={{ color: c.mut }}>›</Text>
              </Row>
              {hi && a.note ? <Muted small>{a.note}</Muted> : null}
            </Pressable>;
          })}
        </Collapsible>;
      })() : null}

      <Collapsible title={t('where.title')}><Where barcode={p.id} liquid={liquid} /></Collapsible>

      {p.micronutrients?.length > 0 ? <Collapsible title={t('simple.microSec')}>
        {p.micronutrients.map((m: any) => <View key={m.key} style={{ marginVertical: 6 }}>
          <Row spread><Text style={{ color: c.ink }}>{t('micro.' + m.key)}</Text><Muted small>{m.amount} {m.unit} · {m.nrv_pct}%</Muted></Row><Bar value={Math.min(1, m.nrv_pct / 100)} />
        </View>)}
        <Muted small>{t('micro.note')}</Muted>
      </Collapsible> : null}

      <Collapsible title={t('simple.ingSec')}>
        <Muted>{p.ingredientsText || t('product.noIng')}</Muted>
        <View style={{ marginTop: 8 }}>{p.allergens.length ? <Row wrap>{p.allergens.map((a: string) => <Pill key={a} tone="w">{a}</Pill>)}</Row>
          : <Muted small>{p.ingredientsText ? t('product.allergenNone') : t('product.allergenMissing')}</Muted>}</View>
        <Text style={{ color: c.accent, marginTop: 8 }} onPress={() => Linking.openURL(`https://world.openfoodfacts.org/product/${p.id}`).catch(() => undefined)}>{t('product.correct')}</Text>
      </Collapsible>

      <Text style={{ color: c.accent, marginVertical: 6 }} onPress={() => Linking.openURL(`https://world.openfoodfacts.org/product/${p.id}`).catch(() => undefined)}>{t('score.page')}</Text>
      <Button plain onPress={() => { addCompare(p.id); go(routes.compare); }}>{t('product.compare')}</Button>

      <Sheet open={!!sheet} onClose={() => setSheet(null)} title={sheet ? sheet.toUpperCase() + (info ? ' · ' + info.name : sItem?.name ? ' · ' + sItem.name : '') : ''}>
        {(sItem?.use || sItem?.found) ? <>
          {sItem.use ? <><Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.use')}</Text><Muted>{sItem.use}</Muted></> : null}
          {sItem.found ? <><Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.found')}</Text><Muted>{sItem.found}</Muted></> : null}
        </> : null}
        {info ? <>
          {!sItem?.use ? <><Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.why')}</Text><Muted>{info.why}</Muted></> : null}
          <Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.evidence')}</Text><Muted>{info.evidence}</Muted>
          <Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.regulation')}</Text><Muted>{info.regulation}</Muted>
          <Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.advice')}</Text><Muted>{info.advice}</Muted>
          <Text style={{ color: c.accent, marginTop: 8 }} onPress={() => Linking.openURL(info.source).catch(() => undefined)}>{t('add.source')} : EFSA / UE</Text>
        </> : sItem?.known ? <>
          <Row><Pill tone={sItem.level === 'D' ? 'b' : sItem.level === 'C' ? 'w' : 'g'}>{t('addl.' + sItem.level)}</Pill></Row>
          {sItem.note ? <><Text style={{ color: c.ink, fontWeight: '700', marginTop: 6 }}>{t('add.health')}</Text><Muted>{sItem.note}</Muted></> : null}
          <Text style={{ color: c.accent, marginTop: 8 }} onPress={() => Linking.openURL('https://food.ec.europa.eu/food-safety/food-improvement-agents/additives/database_en').catch(() => undefined)}>{t('add.euDb')}</Text>
        </> : <>
          <Muted>{t('add.unknown')}</Muted>
          <Text style={{ color: c.accent, marginTop: 8 }} onPress={() => Linking.openURL('https://food.ec.europa.eu/food-safety/food-improvement-agents/additives/database_en').catch(() => undefined)}>{t('add.euDb')}</Text>
        </>}
        <Button onPress={() => setSheet(null)}>{t('common.done')}</Button>
      </Sheet>
    </Screen>
  );
}
