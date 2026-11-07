import { useEffect, useState } from 'react';
import { Linking, Text, View } from 'react-native';
import * as Location from 'expo-location';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { friendlyError } from './errors';
import { Button, ChainBadge, Muted, Row, Segmented, useTheme } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const RADIUS = 5; // only branches within 5 km
const dist = (m: number) => (m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`);

/** Where to buy: the chains that list the product, each with its nearest branches. Same source and rules as the web screen. */
export default function Where({ barcode, liquid }: { barcode: string; liquid?: boolean }) {
  const c = useTheme();
  const home = useProfile((st) => st.place);
  const country = useProfile((st) => st.country);
  const mine = ((useProfile((st) => st.chains) ?? []) as string[]).filter((id) => chainsFor(country).some((x) => x.id === id));
  const [res, setRes] = useState<any | null>(null), [useHere, setUseHere] = useState(false);
  const [more, setMore] = useState(false), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false), [adding, setAdding] = useState(false);
  const hasHome = home?.lat != null;
  const pos = (useHere ? null : home?.lat != null ? { lat: home!.lat!, lon: home!.lon! } : null);

  const live = async (): Promise<{ lat: number; lon: number } | null> => {
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (perm.status !== 'granted') return null;
      const p = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low });
      return { lat: p.coords.latitude, lon: p.coords.longitude };
    } catch { return null; }
  };

  const run = async (here: boolean) => {
    setBusy(true); setMsg('');
    const wantLive = here || !hasHome;
    const p = (wantLive ? await live() : null) ?? (hasHome ? { lat: home!.lat!, lon: home!.lon! } : null);
    if (!p) { setMsg(t('where.denied')); setBusy(false); return; }
    try { setRes(await api.retailers(barcode, p.lat, p.lon, RADIUS, mine)); }
    catch (e) { const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); }
    setBusy(false);
  };
  useEffect(() => { run(false); }, [barcode]);

  const confirm = async (id: string) => {
    try { await api.confirmListing(barcode, id); if (pos) setRes(await api.retailers(barcode, pos.lat, pos.lon, RADIUS, mine)); setAdding(false); }
    catch (e) { const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); }
  };
  const route = (lat: number, lon: number) => Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}${pos ? `&origin=${pos.lat},${pos.lon}` : ''}&travelmode=walking`).catch(() => undefined);

  const shown: any[] = more ? (res?.retailers ?? []) : (res?.retailers ?? []).slice(0, 3);
  return (
    <View>
      {busy ? <Muted small>{t('where.loading')}</Muted> : null}
      {hasHome && <Segmented value={useHere ? 'here' : 'home'} onChange={(k) => { if (busy) return; setUseHere(k === 'here'); run(k === 'here'); }} options={[{ key: 'home', label: t('where.refHome') }, { key: 'here', label: t('where.refHere') }]} />}
      {msg ? <Text style={{ color: c.warn, marginVertical: 4 }}>{msg}</Text> : null}
      {res && !res.retailers.length ? <Muted>{t('where.noChain', { r: RADIUS })}{res.far_chains > 0 ? ` ${t('where.farChains', { n: res.far_chains })}` : ''}</Muted> : null}
      {shown.map((x: any) => (
        <View key={x.chain_id} style={{ borderTopWidth: 1, borderTopColor: c.line, paddingVertical: 10 }}>
          <Row spread>
            <Row><ChainBadge id={x.chain_id} /><Text style={{ color: c.ink, fontWeight: '600' }}>{x.chain}</Text></Row>
            <Text style={{ color: c.mut, fontSize: 13 }}>{x.nearest_store ? dist(x.nearest_store.distance_m) : '—'}</Text>
          </Row>
          {(x.stores ?? []).length ? (x.stores as any[]).slice(0, 1).map((st: any, k: number) => (
            <View key={k} style={{ marginTop: 4 }}>
              <Text style={{ color: c.ink, fontSize: 14 }}>{st.name}{st.address ? <Text style={{ color: c.mut }}> · {st.address}</Text> : null}</Text>
              <Text style={{ color: c.mut, fontSize: 12, marginTop: 2 }}>
                {dist(st.distance_m)}
                {st.distance_m > RADIUS * 1000 ? ` · ${t('where.farAway', { r: RADIUS })}` : ''}
                {' · '}<Text style={{ color: c.accent }} onPress={() => route(st.lat, st.lon)}>{t('where.route')}</Text>
              </Text>
            </View>
          )) : <Muted small>{t('where.farOrUnknown', { r: RADIUS })}</Muted>}
          <Text style={{ color: c.mut, fontSize: 12, marginTop: 4 }}>
            {x.price_per100_cents != null ? `${formatCents(Math.round(x.price_per100_cents * 10))}${liquid ? '/L' : '/kg'}` : ''}
            {x.pack_cents != null ? ` · ${formatCents(x.pack_cents)}` : ''}
          </Text>
        </View>
      ))}
      {res && res.retailers.length > 3 ? <Button small plain onPress={() => setMore(!more)}>{more ? t('where.fewer') : t('where.moreChains', { n: res.retailers.length - 3 })}</Button> : null}
      {res ? <>
        <Muted small>{t('where.stockNote')}</Muted>
        <Button small plain onPress={() => setAdding(!adding)}>{t('where.iFoundIt')}</Button>
        {adding ? <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{(res.other_chains ?? []).map((ch: any) => <Button key={ch.chain_id} small onPress={() => confirm(ch.chain_id)}>{ch.chain}</Button>)}</View> : null}
      </> : null}
    </View>
  );
}
