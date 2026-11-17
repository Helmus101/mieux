import { useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { chainsFor } from '@shared/chains';
import { formatCents, isLiquid, unitPrice } from '@shared/utils/format';
import { cachedAlternatives, fetchAlternatives, NEAR_KM } from '@/lib/alternatives';
import { friendlyError } from '@/lib/errors';
import { Body, Button, Card, ChainLogo, Chip, H, Loader, Muted, NavBar, Row, Screen, Segmented, Skeleton, Thumb, haptic } from '@/components/ui';
import { useTheme } from '@/lib/theme';

/* eslint-disable @typescript-eslint/no-explicit-any */
const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim().split(' ').filter(Boolean).map((w) => w.replace(/s$/, '')).join(' ');

export default function Alternatives() {
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const r = useRouter(), c = useTheme();
  const country = useProfile((s) => s.country), home = useProfile((s) => s.place), estimates = useProfile((s) => s.estimates);
  const priorities = useProfile((s) => s.priorities);
  const myChains = (useProfile((s) => s.chains) ?? []).filter((id) => chainsFor(country).some((x) => x.id === id));
  const chainName = (id: string) => chainsFor(country).find((x) => x.id === id)?.name ?? id;
  const vp = useProfile((s) => s.valueProfile) ?? 'budget', setVp = useProfile((s) => s.setValueProfile);
  const hasHome = home?.lat != null;
  const [res, setRes] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const [tries, setTry] = useState(0), [hidden, setHidden] = useState<string[]>([]), [more, setMore] = useState(false), [chain, setChain] = useState<string | null>(null);
  const autoRetry = useRef(0);
  useEffect(() => { autoRetry.current = 0; setHidden([]); setChain(null); setMore(false); }, [barcode]);
  useEffect(() => {
    if (!barcode) return;
    setErr(null);
    let gone = false, retry: ReturnType<typeof setTimeout> | undefined;
    const stale = cachedAlternatives(barcode);
    if (stale) { setRes(stale); setBusy(false); } else setBusy(true);
    fetchAlternatives(barcode)
      .then((x: any) => { if (!gone) setRes(x); })
      .catch((e: any) => {
        if (gone) return;
        if (autoRetry.current < 1 && e?.response?.status !== 404) { autoRetry.current += 1; retry = setTimeout(() => setTry((n) => n + 1), 1200); return; }
        setErr(friendlyError(e));
      }).finally(() => { if (!gone && !retry) setBusy(false); });
    return () => { gone = true; if (retry) clearTimeout(retry); };
  }, [barcode, priorities.join(), estimates, home?.lat, home?.lon, myChains.join(), tries]);

  // Every profile's ranking comes in one answer: pick the chosen profile's order, no new request.
  const sourceRows = (): any[] => {
    let rows = (res?.rankings?.value ?? []) as any[];
    const fallback = !rows.length;
    if (fallback) rows = (res?.rankings?.match ?? res?.alternatives ?? []) as any[];
    const per = new Map<string, any>(((res?.rankings?.profiles?.[vp] ?? []) as any[]).map((x) => [x.code, x]));
    if (!per.size || fallback) return rows;
    return rows.filter((e) => per.has(e.product?.barcode)).map((e) => ({ ...e, value_score: per.get(e.product.barcode).value_score, why: per.get(e.product.barcode).why })).sort((a, b) => b.value_score - a.value_score);
  };
  const list = (ignoreChain = false) => {
    const seen = new Set<string>();
    return sourceRows().filter((e) => {
      if (hidden.includes(e.product.id)) return false;
      if (!ignoreChain && chain && !(e.product.chains ?? []).includes(chain)) return false;
      if (myChains.length && !e.product.chains?.some((x: string) => myChains.includes(x))) return false;
      const key = norm(String(e.product.brand ?? '')) + '|' + norm(String(e.product.name ?? ''));
      if (seen.has(key)) return false;
      seen.add(key); return true;
    });
  };
  const ranked = list(), shown = ranked.slice(0, more ? 10 : 3);
  const none = !!res && !busy && !err && list(true).length === 0;
  const chainOptions = myChains.length ? myChains : chainsFor(country).map((x) => x.id).filter((id) => ((res?.rankings?.value ?? []) as any[]).some((e) => (e.product.chains ?? []).includes(id)));
  const o = res?.original, ou = o ? unitPrice(res.original_price?.per100_cents, res.original_size, res.original_size?.unit === 'ml') : null;

  const diff = (e: any): { text: string; sub?: string; color: string } | null => {
    const op = res?.original_price;
    if (!op || e.price_per_100_cents == null) return null;
    const size = e.size ?? e.product?.quantity;
    if (size?.unit && res?.original_size?.unit && size.unit !== res.original_size.unit) return null;
    const liquid = isLiquid(e.product) || res?.original_size?.unit === 'ml';
    const k = (e.price_per_100_cents - op.per100_cents) * 10, pct = Math.round(((e.price_per_100_cents - op.per100_cents) / op.per100_cents) * 100);
    return { text: `${k < 0 ? '−' : '+'}${formatCents(Math.abs(Math.round(k)))}${liquid ? '/L' : '/kg'}`, color: Math.abs(k) < 1 ? c.mut : k < 0 ? c.accent : c.bad };
  };

  return (
    <Screen title={t('alt.title')}>
      <NavBar />
      <Text style={{ color: c.ink, fontSize: 34, fontWeight: '700', letterSpacing: -0.9 }}>{t('alt.title')}</Text>
      {o && <Muted><Text style={{ fontWeight: '600' }}>{t('alt.replacing')}</Text> {o.name}{o.brand && o.brand.toLowerCase() !== o.name.toLowerCase() ? ' · ' + o.brand : ''}{o.score?.total != null ? ` · ${t('alt.quality')} ${Math.round(o.score.total)}` : ''}{ou ? ` · ${formatCents(ou.perUnitCents)}/${ou.unit}` : ''}</Muted>}
      {!err && <Segmented value={vp} onChange={(k) => setVp(k as 'budget' | 'balanced' | 'nutrition')} options={(['budget', 'balanced', 'nutrition'] as const).map((k) => ({ key: k, label: t(`alt.profile_${k}`) }))} />}
      {!err && <Muted small>{t('alt.profileSub_' + vp)}</Muted>}
      {!none && chainOptions.length > 1 && <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, alignItems: 'center' }}>
        <Chip on={chain == null} onPress={() => setChain(null)}>{t('alt.allChains')}</Chip>
        {chainOptions.map((id) => <Pressable key={id} onPress={() => { haptic('select'); setChain(chain === id ? null : id); }} style={{ borderRadius: 12, padding: 4, borderWidth: 2, borderColor: chain === id ? c.accent : 'transparent' }}><ChainLogo id={id} name={chainName(id)} size={34} /></Pressable>)}
      </ScrollView>}
      {busy && <>{[0, 1, 2, 3].map((n) => <Row key={n}><Skeleton h={60} w={60} /><View style={{ flex: 1, gap: 8 }}><Skeleton h={16} w="80%" /><Skeleton h={13} w="45%" /></View></Row>)}<Loader steps={t('common.stepsAlt').split('|')} slowAfter={30000} onRetry={() => setTry((n) => n + 1)} /></>}
      {err && <Card><H>{err.title}</H><Muted>{err.why}</Muted><Button small onPress={() => setTry((n) => n + 1)}>{t('errs.retry')}</Button></Card>}
      {!busy && !err && (none || !res || !shown.length) && (() => {
        const m = chain ? { title: t('alt.noChainTitle', { c: chainName(chain) }), why: t('alt.noChainWhy'), label: t('alt.allChains'), act: () => setChain(null) }
          : hasHome && res && !(res.rankings?.value?.length) ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: NEAR_KM }), label: t('emptyAlt.nearAction'), act: () => r.push('/profile') }
          : none || !res ? { title: t('emptyAlt.noneTitle'), why: t('emptyAlt.noneWhy'), label: t('product.nf.scanAgain'), act: () => r.replace('/scan') }
          : { title: t('emptyAlt.valueNoneTitle'), why: t('emptyAlt.valueNoneWhy'), label: t('common.back'), act: () => r.back() };
        return (
          <View style={{ alignItems: 'center', gap: 12, paddingVertical: 36, paddingHorizontal: 12 }}>
            <View style={{ width: 72, height: 72, borderRadius: 22, backgroundColor: c.tint, alignItems: 'center', justifyContent: 'center' }}><Ionicons name="search-outline" size={34} color={c.accent} /></View>
            <Text style={{ color: c.ink, fontSize: 22, fontWeight: '700', textAlign: 'center', letterSpacing: -0.4 }}>{m.title}</Text>
            <Muted style={{ textAlign: 'center' }}>{m.why}</Muted>
            <Button primary onPress={m.act}>{m.label}</Button>
          </View>
        );
      })()}
      {res && !busy && shown.map((e: any) => {
        const u = unitPrice(e.price_per_100_cents, e.product?.quantity, isLiquid(e.product)), d = diff(e), vs = e.value_score, q = e.quality_score ?? e.product?.score?.total;
        const cs = (e.product.chains ?? []).filter((id: string) => chainsFor(country).some((x) => x.id === id) && (!myChains.length || myChains.includes(id)));
        const web = e.price_source?.source === 'web_search';
        return (
          <Pressable key={e.product.id} onPress={() => { haptic('select'); r.push(`/product/${e.product.id}`); }} style={{ flexDirection: 'row', gap: 14, paddingVertical: 16, alignItems: 'flex-start', borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: c.line }}>
            <Thumb uri={e.product.imageUrl} size={60} />
            <View style={{ flex: 1, gap: 3 }}>
              <Body bold>{e.product.name}</Body>
              {e.product.brand ? <Muted small>{e.product.brand}</Muted> : null}
              {cs.length > 0 && <Row wrap style={{ gap: 6 }}>{cs.slice(0, 4).map((id: string) => <ChainLogo key={id} id={id} name={chainName(id)} size={22} />)}{cs.length > 4 && <Muted small>+{cs.length - 4}</Muted>}</Row>}
              <Row wrap style={{ gap: 8 }}>
                {vs != null && <Text style={{ color: vs >= 65 ? c.accent : vs >= 40 ? c.warn : c.bad, fontWeight: '700' }}>{vs} {t('alt.valueShort')}</Text>}
                {q != null && <Muted small>{t('alt.quality')} {Math.max(0, Math.min(100, Math.round(q)))}</Muted>}
              </Row>
            </View>
            <View style={{ alignItems: 'flex-end', gap: 2 }}>
              {u ? <Body bold>{web ? '~ ' : ''}{formatCents(u.perUnitCents)}<Text style={{ fontSize: 12 }}>/{u.unit}</Text></Body> : e.pack_cents != null ? <Body bold>{web ? '~ ' : ''}{formatCents(e.pack_cents)}</Body> : <Muted small>{t('alt.noPrice')}</Muted>}
              {d && <Text style={{ color: d.color, fontSize: 13 }}>{d.text}</Text>}
              <Pressable hitSlop={10} accessibilityLabel={t('sub.notComparable')} onPress={async () => { try { await api.substitutionVerdict(barcode!, e.product.id, 'not_comparable'); haptic('warning'); setHidden((h) => [...h, e.product.id]); } catch { haptic('error'); } }}><Text style={{ color: c.mut, fontSize: 18 }}>⚑</Text></Pressable>
            </View>
          </Pressable>
        );
      })}
      {res && !busy && !more && ranked.length > 3 && <Button small plain onPress={() => setMore(true)}>{t('alt.showMore')}</Button>}
    </Screen>
  );
}
