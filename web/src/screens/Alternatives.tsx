import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { cachedAlternatives, fetchAlternatives, NEAR_KM } from '../alternatives';
import PqExplain from '../PqExplain';
import { Bar, Button, Card, ChainLogo, Muted, NavBar, NovaBadge, NutriScore, Pill, Row, Screen, Segmented, Sheet, Skeleton, Loader, Toast, haptic } from '../ui';
import { formatCents, isLiquid, unitPrice } from '@shared/utils/format';
import { routes, useNav } from '../nav';
import Where from '../Where';
import SaveButton from '../SaveButton';
import { friendlyError } from '../errors';

/* eslint-disable @typescript-eslint/no-explicit-any */
const sizeLabel = (q: { amount: number; unit: string }) => (q.amount >= 1000 ? `${Math.round(q.amount / 100) / 10} ${q.unit === 'ml' ? 'L' : 'kg'}`.replace('.', ',') : `${Math.round(q.amount)} ${q.unit}`);

export default function Alternatives() {
  const { barcode } = useParams<{ barcode: string }>();
  const { go, back } = useNav();
  const saved = useProfile((s) => s.priorities), estimates = useProfile((s) => s.estimates);
  const home = useProfile((s) => s.place);
  const hasHome = home?.lat != null;
  const country = useProfile((s) => s.country);
  const myChains = (useProfile((s) => s.chains) ?? []).filter((id) => chainsFor(country).some((c) => c.id === id));
  // "Today" filters start from the saved profile and never write back to it.
  // Quality is judged on nutrition only; the price tabs come from the price rankings, so no price priority is sent.
  const prios = (() => { const q = saved.filter((k) => k !== 'budget' && k !== 'value'); return q.length ? q : ['overall']; })();
  const [tries, setTry] = useState(0); const picked = useRef(false); const [detail, setDetail] = useState<any | null>(null); const radius = NEAR_KM, [diffBy] = useState<'kg' | 'pack'>('kg'), sameSize = false, subMax = 2, [hidden, setHidden] = useState<string[]>([]); const mode = 'similar', pc = 'any'; const [rk, setRk] = useState('value');
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    if (!barcode || !prios.length) return;
    setErr(null);
    let gone = false;
    // The product page usually started this very request already: the answer is in the cache or about to arrive.
    const stale = cachedAlternatives(barcode);
    if (stale) { setR(stale); setBusy(false); } else setBusy(true);   // show the last answer at once, then refresh it
    fetchAlternatives(barcode)
      .then((x: any) => { if (!gone) setR(x); })
      .catch((e: unknown) => { if (!gone) setErr(friendlyError(e)); }).finally(() => { if (!gone) setBusy(false); });
    return () => { gone = true; };
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries]);
  // A missing observed price starts a shared server search. Keep the row pending until
  // that search completes; "no price" must never mean "we have not finished looking".
  const [webP, setWebP] = useState<Record<string, any>>({});
  const [priceState, setPriceState] = useState<Record<string, 'pending' | 'missing'>>({});
  const asked = useRef(new Set<string>());
  const priceAbort = useRef<AbortController | null>(null);
  useEffect(() => {
    asked.current.clear();
    priceAbort.current?.abort();
    priceAbort.current = null;
    setWebP({});
    setPriceState({});
  }, [barcode]);
  const rowOf = (e0: any) => {
    const w = webP[e0.product?.barcode];
    const chains = (e0.product?.chains?.length) ? e0.product.chains : (w?.chains?.length ? w.chains : []);
    const p100 = e0.price_per_100_cents ?? w?.per100_cents;
    const vs = e0.value_score ?? w?.value_score;
    const pack = e0.pack_cents ?? w?.pack_cents;
    const e = w ? {
      ...e0,
      price_per_100_cents: p100,
      value_score: vs,
      pack_cents: pack,
      product: { ...e0.product, chains },
    } : {
      ...e0,
      product: { ...e0.product, chains },
    };
    return ({
      ps_web: !!w || e.price_source?.source === "web_search",
      avail: e.availability,
      notCheaper: !!e.not_cheaper,
      notBetterValue: !!e.not_better_value,
      product: e.product,
      why: e.why,
      tradeoffs: e.tradeoffs ?? [],
      price100: e.price_per_100_cents,
      estimated: e.estimated,
      dominated: e.dominated,
      vs: e.value_score,
      better: e.better_than_yours,
      detail: e.value_detail,
      ps: e.price_score,
      nearby: e.nearby,
      conf: e.price_source?.confidence as string | undefined,
      priceDate: e.price_date ?? e.price_source?.date,
      stale: e.price_stale ?? e.price_source?.stale,
      size: e.size ?? e.product.quantity,
      pack: e.pack_cents,
      ratio: e.size_ratio,
    });
  };
  // What each tab shows: sorted strictly by category requirements.
  const sourceRows = (k: string): any[] => {
    const base = (r?.rankings?.[k === 'match' ? 'quality' : k] ?? []) as any[];
    if (k !== 'value' && k !== 'budget') return base;
    const have = new Set(base.map((x: any) => x.product?.barcode));
    const extra = [
      ...(r?.rankings?.quality ?? []),
      ...(r?.rankings?.closest ?? []),
      ...(r?.alternatives ?? []).map((a: any) => (a.product ? a : { product: a })),
    ].filter((x: any) => {
      const bc = x.product?.barcode;
      if (!bc || have.has(bc)) return false;
      const w = webP[bc];
      const p100 = x.price_per_100_cents ?? w?.per100_cents;
      if (p100 == null) return false;
      have.add(bc);
      return true;
    });
    return [...base, ...extra];                                      // + candidates priced by the web search
  };
  const listOf = (k: string) => sourceRows(k).map(rowOf).filter((e: any) => {
    if (hidden.includes(e.product.id)) return false;
    if (myChains.length && !e.product.chains?.some((c: string) => myChains.includes(c))) return false;   // the person picked their shops: a shop found later by the price search counts too
    if (k === 'closest') return true;                              // genuine substitutes, price or availability not required
    if (k === 'budget') { const op = r?.original_price?.per100_cents; return e.price100 != null && (op == null || e.price100 < op); }   // cheaper than yours only, cheapest first
    if (k === 'match') { const os0 = r?.original?.score?.total; return os0 == null || (e.product.score?.total ?? -1) > os0; }   // better quality only: never a product scoring the same or lower
    { const ov = r?.rankings?.original_value_score; return e.price100 != null && (ov == null || e.vs == null || e.vs > ov); }   // value: only a better price-quality score than yours
  });
  // Products with a known supermarket come first (Quality and Price-quality tabs, each group in its own order); on the price tab the cheapest stays first and chains only break ties.
  const nCh = (e: any) => (e.product.chains?.length ?? 0);
  const ranked = (() => {
    const l = listOf(rk);
    if (rk === 'budget') return l.map((e: any, i: number) => [e, i] as const).sort((a: any, b: any) => (a[0].price100 - b[0].price100) || (nCh(b[0]) - nCh(a[0])) || (a[1] - b[1])).map((x: any) => x[0]);
    const o = rk === 'value' ? [...l].sort((a: any, b: any) => (b.vs ?? -1) - (a.vs ?? -1)) : l;
    return [...o.filter((e: any) => nCh(e) > 0), ...o.filter((e: any) => nCh(e) === 0)];
  })();
  const shown = ranked.slice(0, 10);
  useEffect(() => {
    if (busy || !r) return;
    const allCands = [
      ...(r?.rankings?.quality ?? []),
      ...(r?.rankings?.closest ?? []),
      ...(r?.rankings?.value ?? []),
      ...(r?.rankings?.budget ?? []),
      ...(r?.alternatives ?? []).map((a: any) => (a.product ? a : { product: a })),
    ];
    const todo = Array.from(new Set(allCands
      .filter((c: any) => {
        const bc = c.product?.barcode;
        return bc && c.product?.quantity && c.price_per_100_cents == null && !asked.current.has(bc);
      })
      .map((c: any) => c.product.barcode as string))).slice(0, 32);
    if (!todo.length) return;
    todo.forEach((c) => asked.current.add(c));
    const controller = new AbortController();
    priceAbort.current?.abort();
    priceAbort.current = controller;
    setPriceState((current) => ({ ...current, ...Object.fromEntries(todo.map((c) => [c, 'pending'])) }));
    // The API returns `pending` when the same server-side search is still running.
    // Rechecking that work avoids duplicate provider calls and keeps the result honest.
    void (async () => {
      for (let i = 0; i < todo.length && !controller.signal.aborted; i += 8) {
        const batch = todo.slice(i, i + 8);
        let pending = batch;
        while (pending.length && !controller.signal.aborted) {
          try {
            const result = await api.getWebPriceBatch(pending, controller.signal);
            if (controller.signal.aborted) return;
            const stillPending = new Set(result.pending);
            const complete = pending.filter((c) => !stillPending.has(c));
            if (complete.length) {
              setWebP((current) => ({ ...current, ...Object.fromEntries(complete.filter((c) => result.prices[c]).map((c) => [c, result.prices[c]])) }));
              setPriceState((current) => ({ ...current, ...Object.fromEntries(complete.map((c) => [c, 'missing'])) }));
            }
            pending = result.pending;
            if (pending.length) await new Promise((resolve) => setTimeout(resolve, 1500));
          } catch {
            if (!controller.signal.aborted) {
              // A transport failure is not evidence that a price is unavailable. Keep
              // the row pending; the next pass can reuse the existing server search.
              await new Promise((resolve) => setTimeout(resolve, 2000));
            }
          }
        }
      }
    })();
    return () => controller.abort();
  }, [busy, r, barcode]);
  const allUnpriced = r ? Array.from(new Set([
    ...(r.rankings?.quality ?? []), ...(r.rankings?.closest ?? []),
    ...(r.rankings?.value ?? []), ...(r.rankings?.budget ?? []),
    ...(r.alternatives ?? []).map((a: any) => (a.product ? a : { product: a })),
  ].filter((e: any) => e.product?.barcode && e.product?.quantity && e.price_per_100_cents == null).map((e: any) => e.product.barcode))).slice(0, 32) : [];
  const webBusy = allUnpriced.some((barcode) => priceState[barcode] !== 'missing' && !webP[barcode]);
  // Nothing at all in any tab (once the price search has finished): no tabs, one plain note saying there is no alternative.
  const none = !!r && !busy && !webBusy && !err && ['value', 'match', 'closest'].every((k) => listOf(k).length === 0);   // never more than 10 per tab, after the strict filters
  // Price-quality first, then cheapest, then better quality. The price tab must stay
  // reachable even while candidate prices are arriving.
  const tabs = r ? [{ key: 'value', label: t('rank.value') }, { key: 'budget', label: t('rank.budget') }, { key: 'match', label: t('rank.match') }].filter((x) => x.key !== 'match' || listOf('match').length > 0) : [];
  useEffect(() => { if (r && !tabs.some((x) => x.key === rk)) setRk(tabs[0]?.key ?? 'value'); }, [r, tabs.map((x) => x.key).join()]);
  const nothingNear = hasHome && !!r && ['budget', 'value', 'quality'].every((k) => !(r.rankings?.[k]?.length));  // nothing sold within the radius at all, whatever the tab
  // Only the difference against the scanned product is shown in the list (per kilo/litre, or per pack); real prices are in the details.
  const showPrice = rk === 'budget' || rk === 'value';   // price differences belong to the price tabs only
  const diffOf = (e: any): { text: string; tone: string; sub?: string } | null => {
    const o = r?.original_price;
    if (!o || !showPrice) return null;
    const liquid = isLiquid(e.product) || r?.original_size?.unit === 'ml';
    const fmt = (c: number) => `${c < 0 ? '−' : '+'}${formatCents(Math.abs(Math.round(c)))}`;
    const tone = (c: number) => (Math.abs(c) < 1 ? 'var(--mut)' : c < 0 ? 'var(--accent)' : 'var(--bad)');
    if (diffBy === 'pack') {
      // FIX: Only show pack difference when sizes are equivalent, otherwise it's misleading
      if (e.pack == null || o.pack_cents == null) return null;
      const eSize = e.size?.amount || 0;
      const oSize = r?.original_size?.amount || 0;
      // Only show pack difference if sizes are within 10% of each other
      if (Math.abs(eSize - oSize) / Math.max(eSize, oSize) > 0.1) return null;
      const c = e.pack - o.pack_cents;
      return { text: `${fmt(c)} ${t('diff.perPack')}`, tone: tone(c), sub: e.price100 != null ? (() => { const k = (e.price100 - o.per100_cents) * 10; return `${fmt(k)}${liquid ? '/L' : '/kg'}`; })() : undefined };
    }
    if (e.price100 == null) return null;
    const k = (e.price100 - o.per100_cents) * 10, pct = Math.round(((e.price100 - o.per100_cents) / o.per100_cents) * 100);
    return { text: `${fmt(k)}${liquid ? '/L' : '/kg'}`, tone: tone(k), sub: `${pct > 0 ? '+' : ''}${pct} % ${t('diff.vs')}` };
  };
  const detailBody = (e: any) => (<>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}><SaveButton product={e.product} /></div>
              {(() => {
                const q = e.product.score?.total, oq = r?.original?.score?.total, dq = q != null && oq != null ? q - oq : null;
                const d = diffOf(e), u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
                const unitTxt = u ? `${formatCents(u.perUnitCents)}/${u.unit === 'L' ? 'L' : 'kg'}` : null;
                return <div className="sumcard">
                  <div className="sum3">
                    <div><span className="mut sm">{t('alt.sumQ')}</span><b>{q ?? '—'}</b>{q != null && <Bar value={q / 100} />}{dq != null && <span className={'dl ' + (dq > 0 ? 'up' : dq < 0 ? 'down' : '')}>{dq === 0 ? t('score.same') : `${dq > 0 ? '+' : '−'}${Math.abs(dq)} ${t('score.pts')}`}</span>}</div>
                    {unitTxt && <div><span className="mut sm">{t('alt.sumP')}</span><b className="sm2">{unitTxt}</b>{d && <span className="dl" style={{ color: d.tone }}>{d.text}</span>}</div>}
                    {e.vs != null && <div><span className="mut sm">{t('alt.sumV')}</span><b>{e.vs}</b><Bar value={e.vs / 100} /></div>}
                  </div>
                  {e.tradeoffs?.length > 0 && <div className="flags" style={{ margin: '14px 0 0' }}>{e.tradeoffs.slice(0, 2).map((x: string) => <span key={x} className="pill w">{x}</span>)}</div>}
                </div>;
              })()}
              {(() => { const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product)); return u ? <p className="mut sm" style={{ margin: '0 0 6px' }}>{t('diff.real')} : <b>{t(u.unit === 'L' ? 'simple.perL' : 'simple.perKg', { p: formatCents(u.perUnitCents) })}</b>{e.pack != null ? ` · ${t('size.pack', { s: e.size?.amount ? sizeLabel(e.size) : '' })} ${formatCents(e.pack)}` : ''}</p> : null; })()}
              {e.dominated && <p className="mut sm" style={{ margin: '0 0 6px' }}>{t('alt.dominated')}</p>}
              <Row wrap><NutriScore grade={e.product.nutriScore} /><NovaBadge group={e.product.novaGroup} estimated={e.product.novaEstimated} />{e.estimated && <Pill tone="w">{t('est.pill')}</Pill>}{e.conf && !e.estimated && <Pill tone={e.conf === 'low' ? 'w' : 'g'}>{t('alt.conf_' + e.conf)}</Pill>}{e.product.frEvidence === 'off_tag' && <Pill tone="g">{t('where.toConfirm')}</Pill>}</Row>
                            <Row wrap>
                <Button primary onPress={() => { setDetail(null); go(routes.product(e.product.id)); }}>{t('alt.seeProduct')}</Button>
                <Button small plain onPress={async () => { try { await api.substitutionVerdict(barcode!, e.product.id, 'not_comparable'); haptic('warning'); setHidden((h) => [...h, e.product.id]); setDetail(null); setNote(t('sub.thanks')); setTimeout(() => setNote(null), 2000); } catch { /* offline: keep it */ } }}><span style={{ marginRight: 6 }}>⚑</span>{t('sub.notComparable')}</Button>
              </Row>
              <h3 style={{ marginTop: 24 }}>{t('where.title')}</h3><Where barcode={e.product.id} liquid={isLiquid(e.product)} />
              {e.product.chains?.length > 0 && <div className="logos">{e.product.chains.slice(0, 6).map((c: string) => <ChainLogo key={c} id={c} size={22} />)}{(e.product.chains?.length ?? 0) > 6 && <span className="mut sm">+{e.product.chains.length - 6}</span>}</div>}
  </>);
  return (
    <Screen>
      <NavBar onBack={back} />
      <h1 className="atitle">{t('alt.title')}</h1>
      {r?.original && <p className="mut asub">{r.original.name}{r.original.brand && r.original.brand.toLowerCase() !== r.original.name.toLowerCase() ? ' · ' + r.original.brand : ''}</p>}
      {!none && tabs.length > 1 && <Segmented value={rk} onChange={(k) => { picked.current = true; setRk(k); }} options={tabs} />}
      {!none && rk === 'value' && <p className="mut sm" style={{ margin: '8px 0 0' }}><PqExplain label /></p>}
      {!none && r?.original_price?.per100_cents != null && <p className="yours"><span>{t('diff.yours')} : <b>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</b></span></p>}
      {busy && <>
        <div className="skel-seg" aria-hidden><Skeleton h={44} /></div>
        <div className="alist" aria-hidden>{[0, 1, 2, 3].map((n) => (
          <div key={n} className="arow skel-arow"><Skeleton h={60} w={60} /><div><Skeleton h={16} w="80%" /><Skeleton h={13} w="45%" /><Skeleton h={28} w={44} /></div><Skeleton h={20} w={64} /></div>
        ))}</div>
        <Loader quiet slowAfter={30000} steps={t('common.stepsAlt').split('|')} onRetry={() => setTry((n) => n + 1)} />
      </>}
      {err && <Card><b>{err.title}</b><Muted>{err.why}</Muted><Button small onPress={() => setTry((n) => n + 1)}>{t('errs.retry')}</Button></Card>}
      {none && <Card><b>{t('emptyAlt.noneTitle')}</b><p className="mut" style={{ margin: '10px 0 0' }}>{t('emptyAlt.noneWhy')}</p></Card>}
      {r && !busy && !none && !shown.length && (() => {
        const os = r?.original?.score?.total;
        const m = nothingNear ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: radius }), action: <Button small onPress={() => go(routes.profile)}>{t('emptyAlt.nearAction')}</Button> }
          : rk === 'closest' ? { title: t('rank.noClosest'), why: t('rank.closestSub') }
          : rk === 'match' ? { title: t('emptyAlt.qualityTitle'), why: os != null ? t('emptyAlt.qualityWhy', { s: os }) : t('emptyAlt.qualityWhyNoScore') }
          : r?.rankings?.no_baseline ? { title: t('emptyAlt.noPriceTitle'), why: t('emptyAlt.noPriceWhy') }
          : rk === 'budget' ? { title: t('emptyAlt.cheaperTitle'), why: t('emptyAlt.cheaperWhy') }
          : r?.rankings?.original_value_score != null ? { title: t('emptyAlt.betterValueTitle'), why: t('emptyAlt.betterValueWhy', { s: r.rankings.original_value_score }) }
          : { title: t('emptyAlt.valueTitle'), why: t('emptyAlt.valueWhy') };
        return <Card><b>{m.title}</b><p className="mut" style={{ margin: '10px 0 0' }}>{m.why}</p>{m.action && <div style={{ marginTop: 14 }}>{m.action}</div>}</Card>;
      })()}
      {r && !busy && rk === 'budget' && shown.length > 0 && <p className="mut sm">{t('alt.cheapestNote')}</p>}
      {r && !busy && <div className="alist">{shown.map((e: any, idx: number) => {
        const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
        const d = diffOf(e);
        const w = webP[e.product.barcode];
        const chains = ((e.product.chains?.length ? e.product.chains : w?.chains) ?? []) as string[];
        return (
          <article key={e.product.id} className={'arow' + (idx === 0 ? ' top' : '')} onClick={() => { haptic('tap'); setDetail(e); }}>
            {e.product.imageUrl ? <img src={e.product.imageUrl} alt="" loading="lazy" decoding="async" width={60} height={60} /> : <span className="noimg" />}
            <div className="amain">
              <div className="aname">{e.product.name}</div>
              <div className="abrand">{e.product.brand}</div>
              <div className="ameta">
                {e.product.score && <span className={'tile ' + (rk === 'match' ? 'main' : 'sub')}><span className="tile-row"><span className={'stile sm ' + (e.product.score.tone === 'b' ? 'b' : e.product.score.tone === 'w' ? 'w' : 'g')}><b>{e.product.score.total}</b></span>
                  {rk === 'match' && r?.original?.score && (() => { const dd = e.product.score.total - r.original.score.total; return dd !== 0 ? <em className={dd > 0 ? 'up' : 'down'}>{dd > 0 ? '+' : '−'}{Math.abs(dd)}</em> : null; })()}</span>
                  <small className="cap">{t('alt.sumQ')}</small></span>}
                {e.vs != null && rk !== 'match' && <span className={'tile ' + (rk === 'value' ? 'main' : 'sub')} title={t('score.pqHint')}><span className="tile-row"><span className={'stile sm ' + (e.vs >= 65 ? 'g' : e.vs >= 40 ? 'w' : 'b')}><b>{e.vs}</b></span></span><small className="cap">{t('score.pq')}</small></span>}
              </div>
              {chains.length > 0 && <div className="logos">{chains.slice(0, 5).map((c: string) => <ChainLogo key={c} id={c} size={20} />)}{chains.length > 5 && <span className="mut sm">+{chains.length - 5}</span>}</div>}
            </div>
            <div className="aprice">
              {u ? <b>{e.ps_web ? '~ ' : ''}{formatCents(u.perUnitCents)}<small>/{u.unit}</small></b>
                : e.pack != null ? <b>{formatCents(e.pack)}</b>
                : w?.per100_cents != null ? <b>~ {formatCents(Math.round(w.per100_cents * 10))}<small>/{isLiquid(e.product) ? 'L' : 'kg'}</small></b>
                : w?.pack_cents != null ? <b>~ {formatCents(w.pack_cents)}</b> : null}
              {u == null && e.pack == null && w?.per100_cents == null && w?.pack_cents == null && (priceState[e.product.barcode] === 'missing' ? <span className="mut sm">{t('alt.noPrice')}</span> : <span className="mut sm"><span className="mini-ring" />{t('alt.pricing')}</span>)}
              {e.stale && !e.ps_web && <span className="mut sm">{t('alt.conf_low')}</span>}
              {d && rk === 'budget' && <span className="sm adiff" style={{ color: d.tone }}>{d.text}</span>}
            </div>
          </article>);
      })}</div>}
      <Sheet open={!!detail} onClose={() => setDetail(null)} title={detail?.product.name}>{detail && detailBody(detail)}</Sheet>
      <Toast text={note} />
    </Screen>
  );
}
