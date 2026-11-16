import { useEffect, useState } from 'react';
import { Linking, Pressable, View } from 'react-native';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { friendlyError } from '@/lib/errors';
import { Body, ChainLogo, Muted, Row, haptic } from './ui';
import { useTheme } from '@/lib/theme';

/* eslint-disable @typescript-eslint/no-explicit-any */
const RADIUS = 5;
const dist = (m: number) => (m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`);
const norm = (d: any) => ({ ...(d ?? {}), retailers: Array.isArray(d?.retailers) ? d.retailers : [], far_chains: d?.far_chains ?? 0 });

/** Where to buy: chains listing the product with the nearest branch to the home address (set in Profile). */
export default function Where({ barcode, liquid }: { barcode: string; liquid?: boolean }) {
  const c = useTheme();
  const home = useProfile((s) => s.place), country = useProfile((s) => s.country);
  const mine = (useProfile((s) => s.chains) ?? []).filter((id) => chainsFor(country).some((x) => x.id === id));
  const [res, setRes] = useState<any>(null), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false), [more, setMore] = useState(false);
  const hasHome = home?.lat != null && home?.lon != null;
  useEffect(() => {
    if (!hasHome) { setMsg(t('where.setHome')); return; }
    let live = true;
    setBusy(true); setMsg('');
    api.retailers(barcode, home!.lat!, home!.lon!, RADIUS, mine)
      .then((d: any) => { if (live) setRes(norm(d)); })
      .catch((e: any) => { if (live) { const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); } })
      .finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [barcode, home?.lat, home?.lon, mine.join()]);
  const rows: any[] = more ? res?.retailers ?? [] : (res?.retailers ?? []).slice(0, 3);
  return (
    <View style={{ gap: 10 }}>
      {busy && <Muted small>{t('where.loading')}</Muted>}
      {msg ? <Muted style={{ color: c.warn }}>{msg}</Muted> : null}
      {res && !res.retailers.length && <Muted>{t('where.noChain', { r: RADIUS })}{res.far_chains > 0 ? ` ${t('where.farChains', { n: res.far_chains })}` : ''}</Muted>}
      {rows.map((x) => {
        const st = (x.stores ?? [])[0];
        return (
          <Row key={x.chain_id} style={{ alignItems: 'flex-start' }}>
            <ChainLogo id={x.chain_id} name={x.chain} size={36} />
            <View style={{ flex: 1 }}>
              {st?.address ? <Muted small>{st.address}</Muted> : !st ? <Muted small>{t('where.farOrUnknown', { r: RADIUS })}</Muted> : null}
              {st && <Pressable onPress={() => { haptic(); Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${st.lat},${st.lon}&origin=${home!.lat},${home!.lon}&travelmode=walking`); }}><Body style={{ color: c.accent, fontSize: 14 }}>{t('where.route')}</Body></Pressable>}
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Body bold>{x.nearest_store ? dist(x.nearest_store.distance_m) : '—'}</Body>
              {x.price_per100_cents != null && <Muted small>{formatCents(Math.round(x.price_per100_cents * 10))}{liquid ? '/L' : '/kg'}</Muted>}
              {x.pack_cents != null && <Muted small>{formatCents(x.pack_cents)}</Muted>}
            </View>
          </Row>
        );
      })}
      {res && res.retailers.length > 3 && <Pressable onPress={() => { haptic(); setMore(!more); }}><Body style={{ color: c.accent }}>{more ? t('where.fewer') : t('where.moreChains', { n: res.retailers.length - 3 })}</Body></Pressable>}
      {res && <Muted small>{t('where.stockNote')}</Muted>}
    </View>
  );
}
