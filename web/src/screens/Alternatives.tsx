import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { readCache, writeCache } from '../swr';
import PqExplain from '../PqExplain';
import { Bar, Button, Card, ChainLogo, Muted, NavBar, NovaBadge, NutriScore, Pill, Row, Screen, Segmented, Sheet, Skeleton, Loader, Toast, haptic } from '../ui';
import { formatCents, isLiquid, unitPrice } from '@shared/utils/format';
import { routes, useNav } from '../nav';
import Where from '../Where';
import SaveButton from '../SaveButton';
import { friendlyError } from '../errors';

/* eslint-disable @typescript-eslint/no-explicit-any */
const NEAR_KM = 5; // only products sold at a chain with a branch within 5 km of home: fixed, not a setting
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
  const [tries, setTry] = useState(0); const picked = useRef(false); const [detail, setDetail] = useState<any | null>(null); const radius = NEAR_KM, [diffBy, setDiffBy] = useState<'kg' | 'pack'>('kg'), sameSize = false, subMax = 2, [hidden, setHidden] = useState<string[]>([]); const mode = 'similar', pc = 'any'; const [rk, setRk] = useState('value');
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    if (!barcode || !prios.length) return;
    setErr(null);
    const ck = `alt:${barcode}:${prios.join()}:${myChains.join()}`;
    const stale = readCache<any>(ck);
    if (stale) { setR(stale); setBusy(false); } else setBusy(true);   // show the last answer at once, then refresh it
    api.getAlternatives(barcode, { priorities: prios, category_mode: mode, limit: 20, substitution_max: subMax, same_size: sameSize, chains: myChains, price_constraint: pc, approximate: estimates, ...(hasHome ? { location: { lat: home!.lat, lon: home!.lon, radius_km: NEAR_KM } } : {}) })
      .then((x: any) => { setR(x); writeCache(ck, x); })
      .catch((e: unknown) => setErr(friendlyError(e))).finally(() => setBusy(false));
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries]);
  // Candidates with no price: one search each for an approximate price and the supermarkets selling it (stored server-side). A found price puts the card into the
  // price and price-quality tabs as it arrives, so the lists fill up to 10 even where the database has no price.
  const [webP, setWebP] = useState<Record<string, any>>({});
  useEffect(() => {
    const rows = (['value', 'budget', 'quality', 'closest'] as const).flatMap((k) => (r?.rankings?.[k] ?? []) as any[]);
    const want = [...new Set(rows.filter((e) => e.price_per_100_cents == null && e.product?.barcode && e.product.quantity).map((e) => e.product.barcode as string))].slice(0, 32);
    if (!want.length) return;
    let live = true;
    (async () => {                                                   // batches of 8, best-ranked first, each shown as it arrives
      for (let i = 0; i < want.length && live; i += 8) {
        try { const m = await api.getWebPrices(want.slice(i, i + 8)); if (live) setWebP((cur) => ({ ...cur, ...m })); } catch { /* keep going */ }
      }
    })();
    return () => { live = false; };
  }, [r]);
  const rowOf = (e0: any) => { const w = e0.price_per_100_cents == null ? webP[e0.product?.barcode] : null; const e = w ? { ...e0, price_per_100_cents: w.per100_cents, value_score: w.value_score, pack_cents: w.pack_cents, product: { ...e0.product, chains: e0.product.chains?.length ? e0.product.chains : (w.chains ?? []) } } : e0; return ({ ps_web: !!w || e.price_source?.source === "web_search", avail: e.availability, notCheaper: !!e.not_cheaper, notBetterValue: !!e.not_better_value, product: e.product, why: e.why, tradeoffs: e.tradeoffs ?? [], price100: e.price_per_100_cents, estimated: e.estimated, dominated: e.dominated, vs: e.value_score, better: e.better_than_yours, detail: e.value_detail, ps: e.price_score, nearby: e.nearby, conf: e.price_source?.confidence as string | undefined, priceDate: e.price_date ?? e.price_source?.date, stale: e.price_stale ?? e.price_source?.stale, size: e.size ?? e.product.quantity, pack: e.pack_cents, ratio: e.size_ratio }); };
  // What each tab shows: sorted strictly by category requirements.
  const sourceRows = (k: string): any[] => {
    const base = (r?.rankings?.[k === 'match' ? 'quality' : k] ?? []) as any[];
    if (k !== 'value' && k !== 'budget') return base;
    const have = new Set(base.map((x: any) => x.product.barcode));
    const extra = [...(r?.rankings?.quality ?? []), ...(r?.rankings?.closest ?? [])].filter((x: any) => x.price_per_100_cents == null && webP[x.product?.barcode] && !have.has(x.product.barcode) && have.add(x.product.barcode));
    return [...base, ...extra];                                      // + candidates priced by the web search
  };
  const listOf = (k: string) => sourceRows(k).map(rowOf).filter((e: any) => {
    if (hidden.includes(e.product.id)) return false;
    if (!(e.product.chains?.length)) return false;                 // only products sold at at least one supermarket chain
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
  const shown = ranked.slice(0, 10);   // never more than 10 per tab, after the strict filters
  // Exactly three tabs, always: price-quality (opens first), price, quality.
  // A tab that has nothing better to show is not offered at all (the three modes, in this order, minus the empty ones).
  const tabs = r ? [{ key: 'value', label: t('rank.value') }, { key: 'budget', label: t('rank.budget') }, { key: 'match', label: t('rank.match') }].filter((x) => listOf(x.key).length > 0) : [];
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
                  {e.detail && <p className="mut sm" style={{ margin: '10px 0 0' }}>{t('score.pqHow', { n: e.detail.nutrition, p: formatCents(Math.round(e.detail.price_per_100_cents * 10)), s: e.detail.size ? sizeLabel(e.detail.size) : '—', d: e.detail.price_date ?? '—' })}</p>}
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
      {tabs.length > 1 && <Segmented value={rk} onChange={(k) => { picked.current = true; setRk(k); }} options={tabs} />}
      <p className="mut sm" style={{ margin: '4px 0 10px' }}>{t('rank.' + rk + 'Sub')}{rk === 'value' && <> <PqExplain label /></>}</p>
      {r?.original_price?.per100_cents != null && <p className="yours"><span>{t('diff.yours')} : <b>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</b>{r.original_size?.amount ? ` · ${sizeLabel(r.original_size)}` : ''}{r.original_price.pack_cents != null ? ` · ${formatCents(r.original_price.pack_cents)}` : ''}</span>
        {showPrice && <button className="linkbtn" onClick={() => setDiffBy(diffBy === 'kg' ? 'pack' : 'kg')} aria-label={t('diff.byKg') + ' / ' + t('diff.byPack')}>{diffBy === 'kg' ? t('diff.byPack') : t('diff.byKg')}</button>}</p>}
      {busy && <><Loader steps={t('common.stepsAlt').split('|')} onRetry={() => setTry((n) => n + 1)} />{[0, 1, 2].map((n) => <Skeleton key={n} h={112} />)}</>}
      {err && <Card><b>{err.title}</b><Muted>{err.why}</Muted><Button small onPress={() => setTry((n) => n + 1)}>{t('errs.retry')}</Button></Card>}
      {r && !busy && !shown.length && (() => {
        const os = r?.original?.score?.total;
        const m = nothingNear ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: radius }), action: <Button small onPress={() => go(routes.profile)}>{t('emptyAlt.nearAction')}</Button> }
          : rk === 'closest' ? { title: t('rank.noClosest'), why: t('rank.closestSub') }
          : rk === 'match' ? { title: t('emptyAlt.qualityTitle'), why: os != null ? t('emptyAlt.qualityWhy', { s: os }) : t('emptyAlt.qualityWhyNoScore') }
          : r?.rankings?.no_baseline ? { title: t('emptyAlt.noPriceTitle'), why: t('emptyAlt.noPriceWhy') }
          : rk === 'budget' ? { title: t('emptyAlt.cheaperTitle'), why: t('emptyAlt.cheaperWhy') }
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
                {e.product.score && <span className={rk === 'match' ? 'main' : 'sub'}><span className={'stile sm ' + (e.product.score.tone === 'b' ? 'b' : e.product.score.tone === 'w' ? 'w' : 'g')}><b>{e.product.score.total}</b></span>{rk === 'match' && <small> {t('score.' + e.product.score.band)}</small>}
                  {rk === 'match' && r?.original?.score && (() => { const dd = e.product.score.total - r.original.score.total; return dd !== 0 ? <em className={dd > 0 ? 'up' : 'down'}>{dd > 0 ? '+' : '−'}{Math.abs(dd)}</em> : null; })()}</span>}
                {e.vs != null && rk !== 'match' && <span className={rk === 'value' ? 'main' : 'sub'} title={t('score.pqHint')}><span className={'stile sm ' + (e.vs >= 65 ? 'g' : e.vs >= 40 ? 'w' : 'b')}><b>{e.vs}</b></span><small> {t('score.pq')}</small></span>}
              </div>
              {chains.length > 0 && <div className="logos">{chains.slice(0, 5).map((c: string) => <ChainLogo key={c} id={c} size={20} />)}{chains.length > 5 && <span className="mut sm">+{chains.length - 5}</span>}</div>}
            </div>
            <div className="aprice">
              {u ? <b>{e.ps_web ? '~ ' : ''}{formatCents(u.perUnitCents)}<small>/{u.unit}</small></b>
                : e.pack != null ? <b>{formatCents(e.pack)}</b>
                : w ? <b>~ {formatCents(Math.round(w.per100_cents * 10))}<small>/{isLiquid(e.product) ? 'L' : 'kg'}</small></b> : null}
              {e.pack != null && u && <span className="mut sm">{formatCents(e.pack)}</span>}
              {d && <span className="sm adiff" style={{ color: d.tone }}>{d.text}</span>}
              <span className="asave" onClick={(ev) => ev.stopPropagation()}><SaveButton product={e.product} /></span>
            </div>
          </article>);
      })}</div>}
      <Sheet open={!!detail} onClose={() => setDetail(null)} title={detail?.product.name}>{detail && detailBody(detail)}</Sheet>
      <Toast text={note} />
    </Screen>
  );
}
