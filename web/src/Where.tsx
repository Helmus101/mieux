import { useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useProfile } from '@shared/stores';
import { CHAIN_LIST } from '@shared/chains';
import { directionsUrl } from './place';
import { Button, ChainLogo, Muted, Row, haptic } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const RADIUS = 5; // only branches within 5 km
const sizeLabel = (q: { amount: number; unit: string }) => (q.amount >= 1000 ? `${Math.round(q.amount / 100) / 10} ${q.unit === 'ml' ? 'L' : 'kg'}`.replace('.', ',') : `${Math.round(q.amount)} ${q.unit}`);
const dist = (m: number) => (m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`);

/** Where to buy: the chains that list the product, each with its nearest branches. Chain discovery and branch location are separate on the server.
 *  The position (current, else home) is used once for the search and not stored by the app. */
export default function Where({ barcode, liquid }: { barcode: string; liquid?: boolean }) {
  const home = useProfile((st) => st.place);
  const mine = (useProfile((st) => st.chains) ?? []).filter((id) => CHAIN_LIST.some((c) => c.id === id));
  const [res, setRes] = useState<any | null>(null), [pos, setPos] = useState<{ lat: number; lon: number } | null>(null), [useHere, setUseHere] = useState(false), [all, setAll] = useState(false);
  const [msg, setMsg] = useState(''), [busy, setBusy] = useState(false), [adding, setAdding] = useState(false);
  const hasHome = home?.lat != null;
  const run = async (here: boolean, everyChain: boolean) => {
    setBusy(true); setMsg('');
    // the reference point is your home when it is set (the closest branch of each chain to where you live); otherwise, or on request, your current position
    const live = (here || !hasHome) ? await new Promise<GeolocationPosition | null>((ok) => navigator.geolocation ? navigator.geolocation.getCurrentPosition(ok, () => ok(null), { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }) : ok(null)) : null;
    const p = live ? { lat: live.coords.latitude, lon: live.coords.longitude } : hasHome ? { lat: home!.lat!, lon: home!.lon! } : null;
    setPos(p); setUseHere(!!live && hasHome === true ? true : !hasHome);
    if (!p) { setMsg(t('where.denied')); setBusy(false); return; }
    try { setRes(await api.retailers(barcode, p.lat, p.lon, RADIUS, everyChain ? [] : mine)); haptic('success'); } catch (e: any) { haptic('error'); setMsg(e.message); }
    setBusy(false);
  };
  const find = () => run(useHere, all);
  const confirm = async (id: string) => { try { await api.confirmListing(barcode, id); if (pos) setRes(await api.retailers(barcode, pos.lat, pos.lon, RADIUS, all ? [] : mine)); setAdding(false); } catch (e: any) { setMsg(e.message); } };
  return (
    <div>
      <Row wrap><Button small onPress={find} disabled={busy}>{busy ? t('where.loading') : t('where.btn')}</Button>
        {res && hasHome && <Button small plain onPress={() => { setUseHere(!useHere); run(!useHere, all); }}>{useHere ? t('chains.fromHome') : t('chains.fromHere')}</Button>}
        </Row>
      {res && mine.length > 0 && <p className="mut sm" style={{ margin: '6px 0' }}>{all ? t('chains.showingAll') : t('chains.filtered', { n: mine.length })} <a style={{ cursor: 'pointer' }} onClick={() => { setAll(!all); run(useHere, !all); }}>{all ? t('chains.useMine') : (res.filtered_out > 0 ? t('chains.showHidden', { n: res.filtered_out }) : t('chains.every'))}</a></p>}
      {res && <p className="mut sm" style={{ margin: '0 0 6px' }}>{t(useHere ? 'chains.sortedHere' : 'chains.sortedHome')}</p>}
      {msg && <p style={{ color: 'var(--warn)' }}>{msg}</p>}
      {res && !res.retailers.length && <Muted>{t('where.noChain', { r: RADIUS })}{res.far_chains > 0 ? ` ${t('where.farChains', { n: res.far_chains })}` : ''}</Muted>}
      {res?.retailers.map((x: any) => (
        <details className="chainrow" key={x.chain_id}>
          <summary>
            <ChainLogo id={x.chain_id} name={x.chain} />
            <span className="nm">{x.chain}</span>
            <span className="dist">{x.nearest_store ? dist(x.nearest_store.distance_m) : <span className="mut">—</span>}</span>
            <span className="pr">{x.price_per100_cents != null ? `${formatCents(Math.round(x.price_per100_cents * 10))}${liquid ? '/L' : '/kg'}` : ''}{x.pack_cents != null && res.size?.amount ? <><br /><span className="sm">{formatCents(x.pack_cents)} · {sizeLabel(res.size)}</span></> : null}</span>
          </summary>
          <div>
            {x.nearest_store
              ? <p style={{ margin: '0 0 6px' }}>{x.nearest_store.distance_m > RADIUS * 1000 && <span className="pill w">{t('where.farAway', { r: RADIUS })}</span>} {x.nearest_store.name}{x.nearest_store.address ? <span className="mut"> · {x.nearest_store.address}</span> : null}{' '}<a target="_blank" rel="noreferrer" href={directionsUrl({ lat: x.nearest_store.lat, lon: x.nearest_store.lon }, pos)}>{t('where.route')}</a></p>
              : <Muted>{t('where.farOrUnknown', { r: RADIUS })}</Muted>}
            {(x.stores ?? []).slice(1).map((st: any, k: number) => <p key={k} className="mut sm" style={{ margin: '0 0 6px' }}>{t('where.second')} : {st.name} · {dist(st.distance_m)} <a target="_blank" rel="noreferrer" href={directionsUrl({ lat: st.lat, lon: st.lon }, pos)}>{t('where.route')}</a></p>)}
            <p className="mut sm" style={{ margin: 0 }}>{x.note ? `${x.note} · ` : ''}{t('where.src_' + x.match_type)}</p>
          </div>
        </details>))}
      {res && <>
        <p className="mut sm">{t('where.stockNote')}{res.filtered_out > 0 ? ` · ${t('chains.more', { n: res.filtered_out })}` : ''}</p>
        <Button small plain onPress={() => setAdding(!adding)}>{t('where.iFoundIt')}</Button>
        {adding && <div className="chips">{res.other_chains.map((c: any) => <button key={c.chain_id} className="chip" onClick={() => confirm(c.chain_id)}>{c.chain}</button>)}</div>}
      </>}
    </div>
  );
}
