import { useEffect, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { directionsUrl } from './place';
import { friendlyError } from './errors';
import { ChainLogo, Muted, Row, Segmented, haptic } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const RADIUS = 5; // only branches within 5 km
const sizeLabel = (q: { amount: number; unit: string }) => (q.amount >= 1000 ? `${Math.round(q.amount / 100) / 10} ${q.unit === 'ml' ? 'L' : 'kg'}`.replace('.', ',') : `${Math.round(q.amount)} ${q.unit}`);
const dist = (m: number) => (m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`);

/** Where to buy: the chains that list the product, each with its nearest branches. Chain discovery and branch location are separate on the server.
 *  The position (current, else home) is used once for the search and not stored by the app. */
/** The server answer with every list guaranteed to be a list, so a thin or odd response can never crash the page. */
const norm = (d: any) => ({ ...(d ?? {}), retailers: Array.isArray(d?.retailers) ? d.retailers : [], other_chains: Array.isArray(d?.other_chains) ? d.other_chains : [], far_chains: d?.far_chains ?? 0 });

export default function Where({ barcode, liquid }: { barcode: string; liquid?: boolean }) {
  const home = useProfile((st) => st.place);
  const country = useProfile((st) => st.country);
  const mine = (useProfile((st) => st.chains) ?? []).filter((id) => chainsFor(country).some((c) => c.id === id));
  const [res, setRes] = useState<any | null>(null), [pos, setPos] = useState<{ lat: number; lon: number } | null>(null), [useHere, setUseHere] = useState(false);
  const all = false;
  const [more, setMore] = useState(false), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false);
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
    try { setRes(norm(await api.retailers(barcode, p.lat, p.lon, RADIUS, everyChain ? [] : mine))); haptic('success'); } catch (e: any) { haptic('error'); const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); }
    setBusy(false);
  };
  useEffect(() => { run(useHere, all); }, [barcode]); // auto-load stores on mount
  return (
    <div>
      <Row wrap>
        {busy && <span className="mut sm"><span className="mini-ring" />{t('where.loading')}</span>}
        {hasHome && <div className="wfrom"><span className="mut sm">{t('where.refLabel')}</span><Segmented value={useHere ? 'here' : 'home'} onChange={(k) => { if (busy) return; setUseHere(k === 'here'); run(k === 'here', all); }} options={[{ key: 'home', label: t('where.refHome') }, { key: 'here', label: t('where.refHere') }]} /></div>}
        </Row>
      {msg && <p style={{ color: 'var(--warn)' }}>{msg}</p>}
      {res && !res.retailers.length && <Muted>{t('where.noChain', { r: RADIUS })}{res.far_chains > 0 ? ` ${t('where.farChains', { n: res.far_chains })}` : ''}</Muted>}
      {(more ? res?.retailers : res?.retailers.slice(0, 3))?.map((x: any) => {
        const st = (x.stores ?? [])[0];
        return (
          <div className="wrow" key={x.chain_id}>
            <ChainLogo id={x.chain_id} name={x.chain} size={36} />
            <div className="wmain">
              <b>{x.chain}</b>
              {st ? ((st.address || (st.name && st.name !== x.chain ? st.name : '')) ? <span className="mut sm">{st.address || st.name}</span> : null) : <span className="mut sm">{t('where.farOrUnknown', { r: RADIUS })}</span>}
              {st && <a className="wroute" target="_blank" rel="noreferrer" href={directionsUrl({ lat: st.lat, lon: st.lon }, pos)}>{t('where.route')}</a>}
            </div>
            <div className="wside">
              <b>{x.nearest_store ? dist(x.nearest_store.distance_m) : '—'}</b>
              {x.price_per100_cents != null && <span className="mut sm">{formatCents(Math.round(x.price_per100_cents * 10))}{liquid ? '/L' : '/kg'}</span>}
              {x.pack_cents != null && res.size?.amount && <span className="mut sm">{formatCents(x.pack_cents)} · {sizeLabel(res.size)}</span>}
            </div>
          </div>);
      })}
      {res && res.retailers.length > 3 && <button className="linkbtn wmore" onClick={() => { haptic('tap'); setMore(!more); }}>{more ? t('where.fewer') : t('where.moreChains', { n: res.retailers.length - 3 })}</button>}
      {res && <p className="mut sm wnote">{t('where.stockNote')}</p>}
    </div>
  );
}
