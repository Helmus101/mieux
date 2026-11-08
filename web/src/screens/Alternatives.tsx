import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { readCache, writeCache } from '../swr';
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
  const rowOf = (e: any) => ({ avail: e.availability, notCheaper: !!e.not_cheaper, notBetterValue: !!e.not_better_value, product: e.product, why: e.why, tradeoffs: e.tradeoffs ?? [], price100: e.price_per_100_cents, estimated: e.estimated, dominated: e.dominated, vs: e.value_score, better: e.better_than_yours, detail: e.value_detail, ps: e.price_score, nearby: e.nearby, conf: e.price_source?.confidence as string | undefined, priceDate: e.price_date ?? e.price_source?.date, stale: e.price_stale ?? e.price_source?.stale, size: e.size ?? e.product.quantity, pack: e.pack_cents, ratio: e.size_ratio });
  // What each tab shows: sorted strictly by category requirements.
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
  // Exactly three tabs, always: price-quality (opens first), price, quality.
  const tabs = [{ key: 'value', label: t('rank.value') }, { key: 'budget', label: t('rank.budget') }, { key: 'match', label: t('rank.match') }];
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
              {e.product.chains?.length > 0 && <div className="logos">{e.product.chains.slice(0, 6).map((c: string) => <ChainLogo key={c} id={c} size={22} />)}{e.product.chains.length > 6 && <span className="mut sm">+{e.product.chains.length - 6}</span>}</div>}
  </>);
  return (
    <Screen>
      <NavBar onBack={back} title={t('alt.title')} />
      <h1>{t('alt.title')}</h1>
      {r?.original && (
        <div style={{ margin: '2px 0 8px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Muted>{r.original.name}</Muted>
          {r?.original?.categories?.length > 0 && (
            <span className="pill" style={{ fontSize: 12 }}>
              {r.original.categories[r.original.categories.length - 1].replace(/^en:|^fr:/, '').replace(/-/g, ' ')}
            </span>
          )}
        </div>
      )}
      {tabs.length > 1 && <Segmented value={rk} onChange={(k) => { picked.current = true; setRk(k); }} options={tabs} />}
      <p className="mut sm" style={{ margin: '4px 0 10px' }}>{t('rank.' + rk + 'Sub')}</p>
      {showPrice && r?.original_price && <Segmented value={diffBy} onChange={(k) => setDiffBy(k as 'kg' | 'pack')} options={[{ key: 'kg', label: t('diff.byKg') }, { key: 'pack', label: t('diff.byPack') }]} />}
      {r?.original_price?.per100_cents != null && <p className="sm" style={{ margin: '2px 0 8px' }}>{t('diff.yours')} : <b>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</b>{r.original_size?.amount ? ` · ${sizeLabel(r.original_size)}` : ''}{r.original_price.pack_cents != null ? ` · ${formatCents(r.original_price.pack_cents)}` : ''}</p>}
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
      {r && !busy && shown.map((e: any, i: number) => {
        return (
          <Card key={e.product.id}>
            <Row>{e.product.imageUrl && <img src={e.product.imageUrl} alt="" loading="lazy" decoding="async" width={56} height={56} style={{ objectFit: 'contain', borderRadius: 12, background: '#fff' }} />}
              <div className="grow"><b>{i + 1}. {e.product.name}</b><Muted>{e.product.brand}</Muted></div><SaveButton product={e.product} /></Row>
            <Row spread>
              {e.product.score ? <span><b style={{ fontSize: 28, letterSpacing: -.5 }}>{e.product.score.total}</b><span className="mut sm">{t('score.outOf')} · {t('score.' + e.product.score.band)}</span>
                {r?.original?.score && (() => { const d = e.product.score.total - r.original.score.total; return <span className="sm" style={{ marginLeft: 8, fontWeight: 600, color: d > 0 ? 'var(--accent)' : d < 0 ? 'var(--bad)' : 'var(--mut)' }}>{d === 0 ? t('score.same') : `${d > 0 ? '+' : '−'}${Math.abs(d)} ${t('score.pts')}`}</span>; })()}</span> : <span />}
              {e.vs != null && <span className="pqchip" title={t('score.pqHint')}><b>{e.vs}</b><small>{t('score.pq')}</small>{e.better != null && <em className={e.better ? 'up' : 'down'}>{e.better ? t('score.pqBetter') : t('score.pqWorse')}</em>}</span>}
              <div style={{ textAlign: 'right' }}>
                {(() => {
                  const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
                  const d = diffOf(e);
                  return (
                    <>
                      {u ? (
                        <div style={{ fontSize: 18, fontWeight: 700 }}>
                          {formatCents(u.perUnitCents)}/{u.unit}
                          {e.pack != null && <span className="mut sm" style={{ fontWeight: 400, marginLeft: 6 }}>({formatCents(e.pack)})</span>}
                        </div>
                      ) : e.pack != null ? (
                        <div style={{ fontSize: 18, fontWeight: 700 }}>{formatCents(e.pack)}</div>
                      ) : null}
                      {d && (
                        <div style={{ marginTop: 2 }}>
                          <span className="sm" style={{ fontWeight: 600, color: d.tone }}>
                            {d.text}
                          </span>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            </Row>
            {(() => {
              const why = [e.why && String(e.why).length <= 120 ? e.why : '', e.conf && !e.estimated && e.price100 != null ? t('alt.conf_' + e.conf) : ''].filter(Boolean).join(' · ');
              return why ? <p className="mut sm" style={{ margin: '6px 0 0' }}>{why}</p> : null;
            })()}
            {e.avail && e.avail.state === 'observed_at_store' && <p style={{ margin: '6px 0 0' }}><Pill tone={e.avail.state === 'observed_at_store' ? 'g' : 'w'}>{e.avail.state === 'observed_at_store' ? t('avail.observed', { s: e.avail.store ?? '?', d: e.avail.date ?? '' }) : e.avail.state === 'seen_at_chain' ? t('avail.chain', { c: e.avail.chain }) : t('avail.listed')}</Pill></p>}
            {e.product.chains?.length > 0 && <div className="logos" style={{ marginTop: 8 }}>{e.product.chains.slice(0, 6).map((c: string) => <ChainLogo key={c} id={c} size={22} />)}{e.product.chains.length > 6 && <span className="mut sm">+{e.product.chains.length - 6}</span>}</div>}
            <Button small plain onPress={() => { haptic('tap'); setDetail(e); }}>{t('simple.moreInfo')}</Button>
          </Card>);
      })}
      <Sheet open={!!detail} onClose={() => setDetail(null)} title={detail?.product.name}>{detail && detailBody(detail)}</Sheet>
      <Toast text={note} />
    </Screen>
  );
}
