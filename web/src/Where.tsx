import { useEffect, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useProfile } from '@shared/stores';
import { CHAIN_LIST } from '@shared/chains';
import { directionsUrl } from './place';
import { friendlyError } from './errors';
import { Button, ChainLogo, Muted, Row, Segmented, haptic } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const RADIUS = 5; // only branches within 5 km
const sizeLabel = (q: { amount: number; unit: string }) => (q.amount >= 1000 ? `${Math.round(q.amount / 100) / 10} ${q.unit === 'ml' ? 'L' : 'kg'}`.replace('.', ',') : `${Math.round(q.amount)} ${q.unit}`);
const dist = (m: number) => (m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`);

/** Where to buy: the chains that list the product, each with its nearest branches. Chain discovery and branch location are separate on the server.
 *  The position (current, else home) is used once for the search and not stored by the app. */
export default function Where({ barcode, liquid }: { barcode: string; liquid?: boolean }) {
  const home = useProfile((st) => st.place);
  const mine = (useProfile((st) => st.chains) ?? []).filter((id) => CHAIN_LIST.some((c) => c.id === id));
  const [res, setRes] = useState<any | null>(null), [pos, setPos] = useState<{ lat: number; lon: number } | null>(null), [useHere, setUseHere] = useState(false);
  const all = false;
  const [more, setMore] = useState(false), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false), [adding, setAdding] = useState(false);
  const hasHome = home?.lat != null;
  const run = async (here: boolean, everyChain: boolean) => {
    setBusy(true); setMsg('');
    // the reference point is your home when it is set (the closest branch of each chain to where you live); otherwise, or on request, your current position
    const wantLive = here || !hasHome;
    const live = wantLive ? await new Promise<GeolocationPosition | null>((ok) => navigator.geolocation ? navigator.geolocation.getCurrentPosition(ok, () => ok(null), { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }) : ok(null)) : null;
    if (here && hasHome && !live) setMsg(t('where.denied'));
    const p = live ? { lat: live.coords.latitude, lon: live.coords.longitude } : hasHome ? { lat: home!.lat!, lon: home!.lon! } : null;
    setPos(p); setUseHere(!!live);
    if (!p) { setMsg(t('where.denied')); setBusy(false); return; }
    try { setRes(await api.retailers(barcode, p.lat, p.lon, RADIUS, everyChain ? [] : mine)); haptic('success'); } catch (e: any) { haptic('error'); const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); }
    setBusy(false);
  };
  useEffect(() => { run(useHere, all); }, [barcode]); // auto-load stores on mount
  const confirm = async (id: string) => { try { await api.confirmListing(barcode, id); if (pos) setRes(await api.retailers(barcode, pos.lat, pos.lon, RADIUS, all ? [] : mine)); setAdding(false); } catch (e: any) { const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); } };
  return (
    <div>
      <Row wrap>
        {busy && <span className="mut sm"><span className="mini-ring" />{t('where.loading')}</span>}
        {hasHome && <div style={{ width: '100%' }}><p className="mut sm" style={{ margin: '0 0 4px' }}>{t('where.refLabel')}</p><Segmented value={useHere ? 'here' : 'home'} onChange={(k) => { if (busy) return; setUseHere(k === 'here'); run(k === 'here', all); }} options={[{ key: 'home', label: t('where.refHome') }, { key: 'here', label: t('where.refHere') }]} /></div>}
        </Row>
      {msg && <p style={{ color: 'var(--warn)' }}>{msg}</p>}
      {res && !res.retailers.length && <Muted>{t('where.noChain', { r: RADIUS })}{res.far_chains > 0 ? ` ${t('where.farChains', { n: res.far_chains })}` : ''}</Muted>}
      {(more ? res?.retailers : res?.retailers.slice(0, 3))?.map((x: any) => (
        <details className="chainrow" key={x.chain_id} open>
          <summary>
            <ChainLogo id={x.chain_id} name={x.chain} />
            <span className="nm">{x.chain}</span>
            <span className="dist">{x.nearest_store ? dist(x.nearest_store.distance_m) : <span className="mut">—</span>}</span>
            <span className="pr">{x.price_per100_cents != null ? `${formatCents(Math.round(x.price_per100_cents * 10))}${liquid ? '/L' : '/kg'}` : ''}{x.pack_cents != null && res.size?.amount ? <><br /><span className="sm">{formatCents(x.pack_cents)} · {sizeLabel(res.size)}</span></> : null}</span>
          </summary>
          <div>
            {(x.stores ?? []).length
              ? (x.stores as any[]).slice(0, 1).map((st: any, k: number) => (
                <div key={k} className="storeline">
                  <div><b>{st.name}</b>{st.address ? <span className="mut sm"> · {st.address}</span> : null}{st.distance_m > RADIUS * 1000 && <> <span className="pill w">{t('where.farAway', { r: RADIUS })}</span></>}</div>
                  <div className="mut sm">{dist(st.distance_m)} · <a target="_blank" rel="noreferrer" href={directionsUrl({ lat: st.lat, lon: st.lon }, pos)}>{t('where.route')}</a></div>
                </div>))
              : <Muted>{t('where.farOrUnknown', { r: RADIUS })}</Muted>}
          </div>
        </details>))}
      {res && res.retailers.length > 3 && <Button small plain onPress={() => { haptic('tap'); setMore(!more); }}>{more ? t('where.fewer') : t('where.moreChains', { n: res.retailers.length - 3 })}</Button>}
      {res && <>
        <p className="mut sm">{t('where.stockNote')}</p>
        <Button small plain onPress={() => setAdding(!adding)}>{t('where.iFoundIt')}</Button>
        {adding && <div className="chips">{res.other_chains.map((c: any) => <button key={c.chain_id} className="chip" onClick={() => confirm(c.chain_id)}>{c.chain}</button>)}</div>}
      </>}
    </div>
  );
}
