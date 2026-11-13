import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { cachedAlternatives, fetchAlternatives, NEAR_KM } from '../alternatives';
import PqExplain from '../PqExplain';
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
  const vp = useProfile((s) => s.valueProfile) ?? 'budget', setVp = useProfile((s) => s.setValueProfile);
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
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries, vp]);
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
  const sourceRows = (k: string): any[] => (r?.rankings?.[k] ?? []) as any[];
  const listOf = (k: string, ignoreChain = false) => {
    const seen = new Set<string>();
    return sourceRows(k).map(rowOf).filter((e: any) => {
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
  const ranked = listOf(rk);
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
  const profileOptions = (['budget', 'balanced', 'nutrition'] as const).map((k) => ({ key: k, label: t(`alt.profile_${k}`) }));
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
      {r?.original && <p className="mut asub">{r.original.name}{r.original.brand && r.original.brand.toLowerCase() !== r.original.name.toLowerCase() ? ' · ' + r.original.brand : ''}</p>}
      {!err && <Segmented value={vp} onChange={(k) => { haptic('tap'); setVp(k as typeof vp); }} options={profileOptions} />}
      {!err && <p className="mut sm" style={{ margin: '8px 0 0' }}>{t(`alt.profileSub_${vp}`)} <PqExplain label /></p>}
      {!none && chainOptions.length > 1 && (
        <div className="chainfilter" role="group" aria-label={t('alt.filterChain')}>
          <button type="button" className={'chainchip all' + (chain == null ? ' on' : '')} aria-pressed={chain == null} onClick={() => setChain(null)}>{t('alt.allChains')}</button>
          {chainOptions.map((id) => <button type="button" key={id} className={'chainchip' + (chain === id ? ' on' : '')} aria-pressed={chain === id} onClick={() => setChain(chain === id ? null : id)}><ChainLogo id={id} name={chainName(id)} size={19} />{chainName(id)}</button>)}
        </div>
      )}
      {!none && r?.original_price?.per100_cents != null && <p className="yours"><span>{t('diff.yours')} : <b>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</b></span></p>}
      {rk === 'value' && r?.rankings?.original_value_score != null && ranked.length > 0 && (ranked[0].vs ?? 0) <= r.rankings.original_value_score && <p className="mut sm" style={{ margin: '8px 0 0' }}>{t('alt.alreadyBestValue')}</p>}
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
        const m = chain ? { title: t('alt.noChainTitle', { c: chainName(chain) }), why: t('alt.noChainWhy'), action: <Button small onPress={() => setChain(null)}>{t('alt.allChains')}</Button> }
          : nothingNear ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: radius }), action: <Button small onPress={() => go(routes.profile)}>{t('emptyAlt.nearAction')}</Button> }
          : { title: t('emptyAlt.valueNoneTitle'), why: t('emptyAlt.valueNoneWhy') };
        void os;
        return <Card><b>{m.title}</b><p className="mut" style={{ margin: '10px 0 0' }}>{m.why}</p>{m.action && <div style={{ marginTop: 14 }}>{m.action}</div>}</Card>;
      })()}
      {r && !busy && <div className="alist">{shown.map((e: any) => {
        const u = unitPrice(e.price100, e.product?.quantity, isLiquid(e.product));
        const d = diffOf(e);
        return (
          <article key={e.product.id} className="arow" onClick={() => { haptic('tap'); go(routes.product(e.product.id)); }}>
            {e.product.imageUrl ? <img src={e.product.imageUrl} alt="" loading="lazy" decoding="async" width={60} height={60} /> : <span className="noimg" />}
            <div className="amain">
              <div className="aname">{e.product.name}</div>
              <div className="abrand">{e.product.brand}</div>
              {(() => {
                // Availability is only shown for stores from Settings, and only the chosen ones when a selection exists.
                const cs = (e.product.chains ?? []).filter((id: string) => chainsFor(country).some((c) => c.id === id) && (!myChains.length || myChains.includes(id)));
                return <div className="achains" title={cs.map(chainName).join(', ')}>{cs.length ? <>{t('alt.seenAt')} {cs.slice(0, 3).map(chainName).join(' · ')}{cs.length > 3 ? ` +${cs.length - 3}` : ''}</> : t('alt.chainUnknown')}</div>;
              })()}
              <div className="ameta">
                {e.vs != null && <span className="tile main" title={e.why}><span className="tile-row"><span className={'stile sm ' + (e.vs >= 65 ? 'g' : e.vs >= 40 ? 'w' : 'b')}><b>{e.vs}</b></span></span><small className="cap">{t('alt.valueScore')}</small></span>}
                {e.q != null && <span className="tile"><span className="tile-row"><span className={'stile sm ' + (e.product.score?.tone === 'b' ? 'b' : e.product.score?.tone === 'w' ? 'w' : 'g')}><b>{e.q}</b></span>
                  {r?.original?.score?.total != null && (() => { const dd = e.q - r.original.score.total; return dd !== 0 ? <em className={dd > 0 ? 'up' : 'down'}>{dd > 0 ? '+' : '−'}{Math.abs(dd)}</em> : null; })()}</span>
                  <small className="cap">{t('alt.quality')}</small></span>}
              </div>
              {e.rel != null && (() => { const pct = Math.round(Math.abs(1 - e.rel) * 100); return <div className="mut sm">{pct < 3 ? t('alt.relMedian') : t(e.rel < 1 ? 'alt.relCheaper' : 'alt.relDearer', { p: pct })} {t('alt.relVs')}{e.confidence === 'low' ? ` · ${t('alt.confidence_low')}` : ''}</div>; })()}
            </div>
            <div className="aprice">
              {u ? <b>{e.ps_web ? '~ ' : ''}{formatCents(u.perUnitCents)}<small>/{u.unit}</small></b>
                : e.pack != null ? <b>{e.ps_web ? '~ ' : ''}{formatCents(e.pack)}</b> : null}
              {u == null && e.pack == null && <span className="mut sm">{t('alt.noPrice')}</span>}
              {d && rk === 'value' && <span className="sm adiff" style={{ color: d.tone }}>{d.text}</span>}
              {rk === 'value' && e.vs != null && r?.rankings?.original_value_score != null && (
                <span className={'valuecmp ' + (e.vs > r.rankings.original_value_score ? 'up' : 'down')}>{e.vs > r.rankings.original_value_score ? t('alt.betterValue') : t('alt.worseValue')}</span>
              )}
              <button className="flagbtn" aria-label={t('sub.notComparable')} title={t('sub.notComparable')} onClick={async (ev) => { ev.stopPropagation(); try { await api.substitutionVerdict(barcode!, e.product.id, 'not_comparable'); haptic('warning'); setHidden((h) => [...h, e.product.id]); setNote(t('sub.thanks')); setTimeout(() => setNote(null), 2000); } catch { /* offline: keep it */ } }}>⚑</button>
            </div>
          </article>);
      })}</div>}
      {r && !busy && !showMore && ranked.length > 3 && <Button small plain onPress={() => { haptic('tap'); setShowMore(true); }}>{t('alt.showMore')}</Button>}
      <Toast text={note} />
    </Screen>
  );
}
