import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { cachedAlternatives, fetchAlternatives, hasAlternatives, NEAR_KM } from '../alternatives';
import { Button, Card, ChainLogo, Muted, NavBar, Screen, Segmented, Skeleton, Loader, Toast, haptic } from '../ui';
import { formatCents, isLiquid, unitPrice } from '@shared/utils/format';
import { routes, useNav } from '../nav';
import { friendlyError } from '../errors';

/* eslint-disable @typescript-eslint/no-explicit-any */

export default function Alternatives() {
  const { barcode } = useParams<{ barcode: string }>();
  const { go, back } = useNav();
  const saved = useProfile((s) => s.priorities), estimates = useProfile((s) => s.estimates);
  const home = useProfile((s) => s.place);
  const hasHome = home?.lat != null;
  const country = useProfile((s) => s.country);
  const myChains = (useProfile((s) => s.chains) ?? []).filter((id) => chainsFor(country).some((c) => c.id === id));
  const chainName = (id: string) => chainsFor(country).find((c) => c.id === id)?.name ?? id.charAt(0).toUpperCase() + id.slice(1);
  // "Today" filters start from the saved profile and never write back to it.
  // Quality is judged on nutrition only; the price tabs come from the price rankings, so no price priority is sent.
  const prios = (() => { const q = saved.filter((k) => k !== 'budget' && k !== 'value'); return q.length ? q : ['overall']; })();
  const [tries, setTry] = useState(0); const radius = NEAR_KM, [diffBy] = useState<'kg' | 'pack'>('kg'), sameSize = false, subMax = 2, [hidden, setHidden] = useState<string[]>([]); const mode = 'similar', pc = 'any'; const rk = 'value'; const [showMore, setShowMore] = useState(false); const [chain, setChain] = useState<string | null>(null);
  // One recommendation score, weighted by what the shopper says matters (budget first by default). Changing it re-asks the API.
  const vpSel = useProfile((s) => s.valueProfile) ?? 'budget', vp = vpSel, setVp = useProfile((s) => s.setValueProfile);
  const [r, setR] = useState<any>(null), [busyRaw, setBusy] = useState(true), [rCode, setRCode] = useState<string | undefined>(undefined), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const busy = busyRaw || rCode !== barcode;   // loading (never the empty message) until the answer for THIS product is here
  const [note, setNote] = useState<string | null>(null), autoRetry = useRef(0);
  useEffect(() => { autoRetry.current = 0; }, [barcode]);
  useEffect(() => {
    if (!barcode || !prios.length) return;
    setErr(null);
    let gone = false, retry: ReturnType<typeof setTimeout> | undefined;
    // The product page usually started this very request already: the answer is in the cache or about to arrive.
    const stale = cachedAlternatives(barcode);
    if (stale && hasAlternatives(stale)) { setR(stale); setRCode(barcode); setBusy(false); } else setBusy(true);   // show the last answer at once, then refresh it
    fetchAlternatives(barcode)
      .then((x: any) => {
        if (gone) return;
        // An empty answer is retried once before it is shown as "no alternatives".
        if (!hasAlternatives(x) && autoRetry.current < 1) { autoRetry.current += 1; retry = setTimeout(() => setTry((n) => n + 1), 800); return; }
        setR(x); setRCode(barcode);
      })
      .catch((e: unknown) => {
        if (gone) return;
        // One quiet retry before showing an error: most failures here are a dropped request or a busy moment on the server.
        if (autoRetry.current < 1 && (e as { response?: { status?: number } })?.response?.status !== 404) { autoRetry.current += 1; retry = setTimeout(() => setTry((n) => n + 1), 1200); return; }
        setErr(friendlyError(e));
      }).finally(() => { if (!gone && !retry) setBusy(false); });
    return () => { gone = true; if (retry) clearTimeout(retry); };
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries]);
  const rowOf = (e: any) => ({
    ps_web: e.price_source?.source === "web_search",
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
    q: e.quality_score ?? e.product?.score?.total,
    rel: e.relative_price as number | undefined,
    confidence: e.confidence as string | undefined,
    better: e.better_than_yours,
    detail: e.value_detail,
    ps: e.price_score,
    nearby: e.nearby,
    conf: e.price_source?.confidence as string | undefined,
    priceDate: e.price_date ?? e.price_source?.date,
    stale: e.price_stale ?? e.price_source?.stale,
    size: e.size ?? e.product?.quantity,
    pack: e.pack_cents,
    ratio: e.size_ratio,
  });
  // The backend ranks by one value score (affordability, nutrition and efficiency, weighted by the chosen profile).
  // Every profile is ranked by the server in the same answer: pick the chosen profile's score and order, no new request.
  const sourceRows = (k: string, vp: string = vpSel): any[] => {
    let rows = (r?.rankings?.[k] ?? []) as any[];
    // The value ranking can legitimately be empty (every candidate's price too old or unverifiable) while the
    // match list still has real alternatives: show those rather than claiming there is nothing.
    const fallback = !rows.length && k === 'value';
    if (fallback) rows = ((r?.rankings?.match ?? r?.alternatives ?? []) as any[]);
    const per = new Map<string, any>(((r?.rankings?.profiles?.[vp] ?? []) as any[]).map((x) => [x.code, x]));
    // On the Nutrition profile an alternative is only worth showing if its quality score beats the scanned product's.
    const oq = r?.original?.score?.total;
    if (vp === 'nutrition' && typeof oq === 'number') rows = rows.filter((e) => { const q = e.quality_score ?? e.product?.score?.total; return typeof q === 'number' && q > oq; });
    if (!per.size || fallback) return rows;
    return rows.filter((e) => per.has(e.product?.barcode)).map((e) => ({ ...e, value_score: per.get(e.product.barcode).value_score, why: per.get(e.product.barcode).why }))
      .sort((a, b) => b.value_score - a.value_score);
  };
  const listOf = (k: string, ignoreChain = false, prof: string = vpSel) => {
    const seen = new Set<string>();
    return sourceRows(k, prof).map(rowOf).filter((e: any) => {
      if (hidden.includes(e.product.id)) return false;
      if (!ignoreChain && chain && !(e.product.chains ?? []).includes(chain)) return false;
      if (myChains.length && !e.product.chains?.some((c: string) => myChains.includes(c))) return false;
      return true;
    }).filter((e: any) => {
      // The same product under another barcode or pack size is one row: keep the best-ranked one.
      const norm = (t: string) => t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, ' ').trim().split(' ').filter(Boolean).map((w) => w.replace(/s$/, '')).join(' ');
      const key = norm(String(e.product.brand ?? '')) + '|' + norm(String(e.product.name ?? ''));
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };
  // A store filter that would leave a single row (or none) is not applied: the whole list stays, rather than one lonely product.
  const ranked = (() => { const f = listOf(rk); return chain && f.length < 2 ? listOf(rk, true) : f; })();
  const shown = ranked.slice(0, showMore ? 10 : 3);
  // Store list on Valeur and Qualité
  const chainOptions = (() => {
    if (myChains.length) return myChains;
    const pool = [
      ...(r?.rankings?.value ?? []),
      ...(r?.alternatives ?? []).map((a: any) => (a.product ? a : { product: a })),
    ];
    return chainsFor(country).map((c) => c.id).filter((id) => pool.some((e: any) => (e.product.chains ?? []).includes(id)));
  })();
  const none = !!r && !busy && !err && listOf('value', true).length === 0;
  // A profile with no alternatives at all is hidden (the chosen one stays, so the screen never loses its own tab).
  const profileOptions = (['budget', 'balanced', 'nutrition'] as const).filter((k) => k === vp || !r || listOf('value', false, k).length > 0).map((k) => ({ key: k, label: t(`alt.profile_${k}`) }));
  // The chosen profile has nothing but another one does: move to the first that has something.
  useEffect(() => {
    if (!r || busy || listOf('value', false, vp).length) return;
    const other = (['budget', 'balanced', 'nutrition'] as const).find((k) => k !== vp && listOf('value', false, k).length > 0);
    if (other) setVp(other);
  }, [r, busy, vp]);
  useEffect(() => { setShowMore(false); }, [barcode, vp]);
  useEffect(() => { setChain(null); }, [barcode]);
  useEffect(() => { if (chain && !chainOptions.includes(chain)) setChain(null); }, [chain, chainOptions.join()]);
  const nothingNear = hasHome && !!r && !(r.rankings?.value?.length);  // nothing sold within the radius at all
  // Only the difference against the scanned product is shown in the list (per kilo/litre, or per pack); real prices are in the details.
  const showPrice = rk === 'value';   // price differences belong to the price-quality tab only
  const diffOf = (e: any): { text: string; tone: string; sub?: string } | null => {
    const o = r?.original_price;
    if (!o || !showPrice) return null;
    // A per-100-unit difference is only valid when both sides share the same unit (g or ml): a candidate with a
    // bad or missing pack size on one side would otherwise silently compare cents-per-100ml against cents-per-100g.
    if (e.size?.unit && r?.original_size?.unit && e.size.unit !== r.original_size.unit) return null;
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
  return (
    <Screen>
      <NavBar onBack={back} />
      <h1 className="atitle">{t('alt.title')}</h1>
      {r?.original && (() => {
        const o = r.original, oq = o.score?.total, ou = unitPrice(r.original_price?.per100_cents, r.original_size ? { ...r.original_size } : undefined, r.original_size?.unit === 'ml');
        return <p className="mut asub"><span className="asub-k">{t('alt.replacing')}</span> {o.name}{o.brand && o.brand.toLowerCase() !== o.name.toLowerCase() ? ' · ' + o.brand : ''}{oq != null && <> · {t('alt.quality')} {Math.round(oq)}</>}{ou && <> · {formatCents(ou.perUnitCents)}/{ou.unit}</>}</p>;
      })()}
      {!err && <Segmented value={vp} onChange={(k) => { haptic('tap'); setVp(k as typeof vp); }} options={profileOptions} />}
      {!err && <p className="mut aprof">{t('alt.profileSub_' + vp)}</p>}
      {!none && chainOptions.length > 1 && (
        <div className="chainfilter" role="group" aria-label={t('alt.filterChain')}>
          <button type="button" className={'chainchip all' + (chain == null ? ' on' : '')} aria-pressed={chain == null} onClick={() => setChain(null)}>{t('alt.allChains')}</button>
          {chainOptions.map((id) => <button type="button" key={id} className={'chainchip' + (chain === id ? ' on' : '')} aria-pressed={chain === id} onClick={() => setChain(chain === id ? null : id)}><ChainLogo id={id} name={chainName(id)} size={19} />{chainName(id)}</button>)}
        </div>
      )}
      {busy && <>
        <div className="skel-seg" aria-hidden><Skeleton h={44} /></div>
        <div className="agrid" aria-hidden>{[0, 1, 2, 3].map((n) => (
          <div key={n} className="acard"><Skeleton h={200} /><div className="atext"><Skeleton h={16} w="70%" /><Skeleton h={13} w="50%" /><Skeleton h={18} w="30%" /></div></div>
        ))}</div>
        <Loader quiet slowAfter={30000} steps={t('common.stepsAlt').split('|')} onRetry={() => setTry((n) => n + 1)} />
      </>}
      {err && <Card><b>{err.title}</b><Muted>{err.why}</Muted><Button small onPress={() => setTry((n) => n + 1)}>{t('errs.retry')}</Button></Card>}
      {none && <Card><b>{t('emptyAlt.noneTitle')}</b><p className="mut" style={{ margin: '10px 0 0' }}>{t('emptyAlt.noneWhy')}</p></Card>}
      {r && !busy && !none && !shown.length && (() => {
        const os = r?.original?.score?.total;
        const m = chain ? { title: t('alt.noChainTitle', { c: chainName(chain) }), why: t('alt.noChainWhy'), action: <Button small onPress={() => setChain(null)}>{t('alt.allChains')}</Button> }
          : r?.already_great ? { title: t('emptyAlt.greatTitle'), why: t('emptyAlt.greatWhy') }
          : nothingNear ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: radius }), action: <Button small onPress={() => go(routes.profile)}>{t('emptyAlt.nearAction')}</Button> }
          : { title: t('emptyAlt.valueNoneTitle'), why: t('emptyAlt.valueNoneWhy') };
        void os;
        return <Card><b>{m.title}</b><p className="mut" style={{ margin: '10px 0 0' }}>{m.why}</p>{m.action && <div style={{ marginTop: 14 }}>{m.action}</div>}</Card>;
      })()}
      {r && !busy && <div className="agrid">{shown.map((e: any, i: number) => {
        const u = unitPrice(e.price100, e.product?.quantity, isLiquid(e.product));
        const d = diffOf(e);
        const cs = (e.product.chains ?? []).filter((id: string) => chainsFor(country).some((c) => c.id === id) && (!myChains.length || myChains.includes(id)));
        const at = cs.length ? `${t('alt.seenAt')} ${cs.slice(0, 2).map(chainName).join(' · ')}${cs.length > 2 ? ` +${cs.length - 2}` : ''}` : t('alt.chainUnknown');
        const open = () => { haptic('tap'); go(routes.product(e.product.id)); };
        return (
          <article key={e.product.id} className="acard" role="button" tabIndex={0} aria-label={e.product.name}
            onClick={open}
            onKeyDown={(ev) => { if (ev.target === ev.currentTarget && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); open(); } }}>
            <div className="aphoto">
              {e.product.imageUrl ? <img src={e.product.imageUrl} alt="" loading={i < 4 ? 'eager' : 'lazy'} decoding="async" /> : <span className="noimg" />}
              {e.vs != null && <span className={'abadge ' + (e.vs >= 65 ? 'g' : e.vs >= 40 ? 'w' : 'b')} title={e.why}>{e.vs} {t('alt.valueShort')}</span>}
              <button className="flagbtn" aria-label={t('sub.notComparable')} title={t('sub.notComparable')} onClick={async (ev) => { ev.stopPropagation(); try { await api.substitutionVerdict(barcode!, e.product.id, 'not_comparable'); haptic('warning'); setHidden((h) => [...h, e.product.id]); setNote(t('sub.thanks')); setTimeout(() => setNote(null), 2000); } catch { /* offline: keep it */ } }}>⚑</button>
            </div>
            <div className="atext">
              <div className="atop">
                <div className="aname">{e.product.name}</div>
                {e.q != null && <span className="aq" title={t('alt.qualityTip')}>★ {Math.max(0, Math.min(100, Math.round(e.q)))}</span>}
              </div>
              <div className="abrand" title={cs.map(chainName).join(', ')}>{[e.product.brand, at].filter(Boolean).join(' · ')}</div>
              <div className="aprice">
                {u ? <b>{e.ps_web ? '~ ' : ''}{formatCents(u.perUnitCents)}<small> /{u.unit}</small></b>
                  : e.pack != null ? <b>{e.ps_web ? '~ ' : ''}{formatCents(e.pack)}</b> : <span className="mut sm">{t('alt.noPrice')}</span>}
                {d && rk === 'value' && <span className="sm adiff" style={{ color: d.tone }}>{d.text}</span>}
              </div>
            </div>
          </article>);
      })}</div>}
      {r && !busy && !showMore && ranked.length > 3 && <Button small plain onPress={() => { haptic('tap'); setShowMore(true); }}>{t('alt.showMore')}</Button>}
      <Toast text={note} />
    </Screen>
  );
}
