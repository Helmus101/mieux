import { useEffect, useRef, useState } from 'react';
import { Animated, PanResponder, Pressable, Text, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { api } from '@shared/api/client';
import { getStrict } from '@shared/config';
import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { writeCache } from '@/lib/cache';
import { EmbeddedContext, Muted, Row, Skeleton, haptic } from './ui';
import { ProductView } from '@/app/product/[barcode]';
import { toneColor, useTheme } from '@/lib/theme';

/* eslint-disable @typescript-eslint/no-explicit-any */
const PRICE_WAIT_MS = 12000;
export const prodKey = (barcode: string, approximate: boolean) => {
  const p = useProfile.getState();
  return `prod:${barcode}:${approximate ? 1 : 0}:${getStrict() ? 1 : 0}:${p.diet ?? 'omnivore'}:${[...(p.allergens ?? [])].sort().join('+')}`;
};

/** A card over the live camera: title and the two scores. Tap it or swipe it up and it opens into the full product page in place (the camera stays behind);
 * swipe that down to shrink it, and swipe the card down to dismiss it (a flick throws it off screen). */
export default function ScanPeek({ code, onExpandedChange, onClose }: { code: string; onExpandedChange?: (open: boolean) => void; onClose: () => void }) {
  const c = useTheme(), ins = useSafeAreaInsets(), { height: H } = useWindowDimensions();
  const [expanded, setExpanded] = useState(false);
  const sheetY = useRef(new Animated.Value(H)).current;
  const expand = () => { haptic('heavy'); setExpanded(true); onExpandedChange?.(true); Animated.spring(sheetY, { toValue: 0, damping: 28, stiffness: 260, mass: 1, useNativeDriver: true }).start(); };
  const collapse = () => { haptic('tap'); onExpandedChange?.(false); Animated.spring(sheetY, { toValue: H, damping: 30, stiffness: 300, mass: 1, useNativeDriver: true }).start(() => { setExpanded(false); onClose(); }); };   // closing the opened product closes the card too
  useEffect(() => () => onExpandedChange?.(false), []);   // closing the card or leaving the tab unlocks the scanner
  const [d, setD] = useState<any>(null), [failed, setFailed] = useState(false), [priceDone, setPriceDone] = useState(false);
  const addScan = useHistory((s) => s.addScan);
  const y = useRef(new Animated.Value(0)).current;
  const pan = useRef(PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dy) > 8 && Math.abs(g.dy) > Math.abs(g.dx),
    onPanResponderMove: (_, g) => y.setValue(Math.max(-24, g.dy)),   // 1:1 with the finger down, a little give upwards
    onPanResponderRelease: (_, g) => {
      if (g.dy < -40 || (g.vy < -0.6 && g.dy < -12)) { Animated.spring(y, { toValue: 0, damping: 20, stiffness: 300, mass: 1, useNativeDriver: true }).start(); if (readyRef.current) expandRef.current(); return; }
      const projected = g.dy + (g.vy * 1000 / 1000) * 0.998 / (1 - 0.998) * 0.1;   // momentum projection
      if (projected > 120) { haptic('tap'); Animated.spring(y, { toValue: 400, velocity: g.vy, damping: 30, stiffness: 300, mass: 1, useNativeDriver: true }).start(onClose); }
      else Animated.spring(y, { toValue: 0, velocity: g.vy, damping: 20, stiffness: 300, mass: 1, useNativeDriver: true }).start();
    },
  })).current;

  const sheetPan = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onPanResponderMove: (_, g) => sheetY.setValue(Math.max(0, g.dy)),
    onPanResponderRelease: (_, g) => { if (g.dy > 110 || g.vy > 0.9) collapseRef.current(); else Animated.spring(sheetY, { toValue: 0, damping: 24, stiffness: 300, mass: 1, useNativeDriver: true }).start(); },
  })).current;
  const collapseRef = useRef(collapse); collapseRef.current = collapse;
  const expandRef = useRef(expand); expandRef.current = expand;
  const readyRef = useRef(false);
  useEffect(() => {
    let live = true; setD(null); setFailed(false); setPriceDone(false); y.setValue(0);
    const giveUp = setTimeout(() => { if (live) setPriceDone(true); }, PRICE_WAIT_MS);
    api.getWebPriceQuick(code).catch(() => undefined).finally(() => { if (live) { clearTimeout(giveUp); setPriceDone(true); } });
    api.getProduct(code).then((x: any) => { if (!live) return; setD(x); writeCache(prodKey(code, false), x); addScan(x.product); api.addScan(code).catch(() => undefined); haptic('success'); })
      .catch(() => { if (live) { setFailed(true); setPriceDone(true); haptic('error'); } });
    return () => { live = false; clearTimeout(giveUp); };
  }, [code]);

  const p = d?.product, sc = p?.score;
  const conflict = (d?.fit ?? []).some((x: any) => (x.priority.startsWith('allergen:') || x.priority.startsWith('diet:')) && x.status === 'conflict');
  const tone = conflict ? 'b' : sc?.tone;
  const pq: number | null = d?.price_context?.value?.value_score ?? null;
  const ready = !!p;
  readyRef.current = ready;
  return (
    <>
    <Animated.View {...pan.panHandlers} style={{ position: 'absolute', left: 12, right: 12, bottom: 96, transform: [{ translateY: y }], opacity: expanded ? 0 : y.interpolate({ inputRange: [0, 160], outputRange: [1, 0], extrapolate: 'clamp' }) }} pointerEvents={expanded ? 'none' : 'auto'}>
      <Pressable disabled={!ready} onPress={expand} accessibilityLabel={t('scan.peekOpen')}
        style={{ backgroundColor: c.bg, borderRadius: 20, padding: 16, gap: 12, shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: 6 } }}>
        <Pressable hitSlop={12} onPress={onClose} style={{ position: 'absolute', top: 10, right: 14, zIndex: 2 }} accessibilityLabel={t('scan.close')}><Text style={{ color: c.mut, fontSize: 22 }}>×</Text></Pressable>
        {failed ? <Muted>{t('scan.peekFailed')}</Muted> : !p ? <><Skeleton h={18} w="60%" /><Skeleton h={14} w="35%" /></> : <>
          <Row style={{ paddingRight: 24 }}>
            {p.imageUrl ? <Image source={{ uri: p.imageUrl }} style={{ width: 52, height: 52, borderRadius: 8, backgroundColor: '#fff' }} contentFit="contain" /> : null}
            <View style={{ flex: 1 }}>
              <Text numberOfLines={2} style={{ color: c.ink, fontSize: 17, fontWeight: '600', letterSpacing: -0.2 }}>{p.name}</Text>
              {p.brand && p.brand.toLowerCase() !== (p.name ?? '').toLowerCase() ? <Muted small>{p.brand}</Muted> : null}
            </View>
          </Row>
          <Row style={{ gap: 28 }}>
            <View><Muted small>{t('score.quality')}</Muted><Text style={{ color: toneColor(tone, c.dark), fontSize: 34, fontWeight: '700', letterSpacing: -1 }}>{sc ? sc.total : '–'}<Text style={{ fontSize: 14, color: c.mut }}>/100</Text></Text><Muted small>{conflict ? t('scan.peekConflict') : sc ? t('score.' + sc.band) : t('score.na')}</Muted></View>
            <View><Muted small>{t('score.value')}</Muted><Text style={{ color: pq == null ? c.mut : toneColor(pq >= 65 ? 'g' : pq >= 40 ? 'w' : 'b', c.dark), fontSize: 34, fontWeight: '700', letterSpacing: -1 }}>{pq ?? '–'}{pq != null ? <Text style={{ fontSize: 14, color: c.mut }}>/100</Text> : null}</Text></View>
          </Row>
          {ready ? <View style={{ backgroundColor: c.accent, borderRadius: 999, minHeight: 44, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 6 }}><Ionicons name="chevron-up" size={18} color={c.accentInk} /><Text style={{ color: c.accentInk, fontWeight: '600', fontSize: 16 }}>{t('scan.peekView')}</Text></View>
            : <Muted small>{t('alt.pricing')}</Muted>}
        </>}
      </Pressable>
    </Animated.View>
    {expanded && (
      <Animated.View style={{ position: 'absolute', left: 0, right: 0, bottom: 0, top: ins.top + 8, backgroundColor: c.bg, borderTopLeftRadius: 20, borderTopRightRadius: 20, overflow: 'hidden', transform: [{ translateY: sheetY }], shadowColor: '#000', shadowOpacity: 0.25, shadowRadius: 18, shadowOffset: { width: 0, height: -6 } }}>
        <View {...sheetPan.panHandlers} accessibilityLabel={t('common.back')} style={{ height: 28, alignItems: 'center', justifyContent: 'center' }}>
          <View style={{ width: 40, height: 5, borderRadius: 3, backgroundColor: c.line }} />
        </View>
        <Pressable hitSlop={12} onPress={collapse} style={{ position: 'absolute', top: 4, right: 14, zIndex: 3 }} accessibilityLabel={t('scan.close')}><Text style={{ color: c.mut, fontSize: 26 }}>×</Text></Pressable>
        <EmbeddedContext.Provider value={{ close: collapse }}><ProductView barcode={code} /></EmbeddedContext.Provider>
      </Animated.View>
    )}
    </>
  );
}
