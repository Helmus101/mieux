/** React Native implementation of the same primitives as web/src/ui/index.tsx. Screens only import from here. */
import { ReactNode, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Image, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View, useColorScheme, ViewStyle } from 'react-native';
import * as hx from './haptics';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, novaColors, nutriScoreColors, radius } from '@shared/theme';
import { t } from '@shared/i18n';

export const useTheme = () => colors[useColorScheme() === 'dark' ? 'dark' : 'light'];
export const haptic = hx.select;

export function Screen({ children, scroll = true }: { children: ReactNode; scroll?: boolean }) {
  const c = useTheme();
  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: c.bg }}>
      {scroll ? <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 48 }} keyboardShouldPersistTaps="handled">{children}</ScrollView> : <View style={{ flex: 1, padding: 16 }}>{children}</View>}
    </SafeAreaView>
  );
}

/** The bar at the top of a screen: back on the left, title in the middle, an action on the right. */
export function NavBar({ title, onBack, right }: { title?: string; onBack?: () => void; right?: ReactNode }) {
  const c = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', minHeight: 44, marginBottom: 4 }}>
      {onBack ? (
        <Pressable onPress={() => { hx.light(); onBack(); }} hitSlop={10} style={{ flexDirection: 'row', alignItems: 'center', paddingRight: 8 }}>
          <Text style={{ color: c.accent, fontSize: 26, marginTop: -3 }}>‹</Text>
          <Text style={{ color: c.accent, fontSize: 16, fontWeight: '500' }}>{t('common.back')}</Text>
        </Pressable>
      ) : <View style={{ width: 24 }} />}
      <Text numberOfLines={1} style={{ flex: 1, textAlign: 'center', color: c.ink, fontSize: 16, fontWeight: '600' }}>{title ?? ''}</Text>
      <View style={{ minWidth: 24, alignItems: 'flex-end' }}>{right}</View>
    </View>
  );
}

/** The Mieux mark and wordmark: the app mark, then "mieux" with the orange full stop. */
export function Brand({ size = 28 }: { size?: number }) {
  const c = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      <View style={{ width: size, height: size, borderRadius: size * 0.28, backgroundColor: c.accent, alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ color: c.accentInk, fontWeight: '800', fontSize: size * 0.58 }}>m</Text>
      </View>
      <Text style={{ color: c.ink, fontSize: size * 0.8, fontWeight: '800', letterSpacing: -0.5 }}>mieux<Text style={{ color: c.warn }}>.</Text></Text>
    </View>
  );
}

export const LargeTitle = ({ children, kicker, sub }: { children: ReactNode; kicker?: string; sub?: string }) => {
  const c = useTheme();
  return (<View style={{ marginBottom: 8 }}>{kicker ? <Text style={{ color: c.accent, fontWeight: '600', letterSpacing: 1.2, fontSize: 13 }}>{kicker}</Text> : null}
    <Text style={{ color: c.ink, fontSize: 32, fontWeight: '700', letterSpacing: -0.4 }}>{children}</Text>{sub ? <Text style={{ color: c.mut, fontSize: 15, marginTop: 2 }}>{sub}</Text> : null}</View>);
};
export const Section = ({ title, children }: { title?: string; children: ReactNode }) => {
  const c = useTheme();
  return (<View>{title ? <Text style={{ color: c.mut, fontSize: 13, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.6, marginTop: 22, marginBottom: 8, marginLeft: 6 }}>{title}</Text> : null}{children}</View>);
};
export const Muted = ({ children, small, style }: { children: ReactNode; small?: boolean; style?: ViewStyle }) => <Text style={[{ color: useTheme().mut, fontSize: small ? 13 : 15 }, style]}>{children}</Text>;
export const Body = ({ children, bold }: { children: ReactNode; bold?: boolean }) => <Text style={{ color: useTheme().ink, fontSize: 16, fontWeight: bold ? '600' : '400' }}>{children}</Text>;
export const Card = ({ children, tint }: { children: ReactNode; tint?: boolean }) => {
  const c = useTheme();
  return <View style={{ backgroundColor: tint ? c.tint : c.card, borderRadius: 18, padding: 16, marginVertical: 8, shadowColor: '#000', shadowOpacity: tint ? 0 : 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: tint ? 0 : 2 }}>{children}</View>;
};
export const Group = ({ children }: { children: ReactNode }) => <View style={{ backgroundColor: useTheme().card, borderRadius: 18, overflow: 'hidden', marginVertical: 8, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 2 }}>{children}</View>;
export function Cell({ children, onPress, last, chevron, image }: { children: ReactNode; onPress?: () => void; last?: boolean; chevron?: boolean; image?: string | null }) {
  const c = useTheme();
  return (<Pressable onPress={onPress ? () => { hx.light(); onPress(); } : undefined} style={({ pressed }) => ({ padding: 14, minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: 10, justifyContent: 'center', backgroundColor: pressed && onPress ? c.line : 'transparent', borderBottomWidth: last ? 0 : StyleSheet.hairlineWidth, borderBottomColor: c.line })}>
    {image ? <Image source={{ uri: image }} style={{ width: 44, height: 44, borderRadius: 8, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
    <View style={{ flex: 1 }}>{children}</View>
    {chevron ? <Text style={{ color: c.mut, fontSize: 20 }}>›</Text> : null}
  </Pressable>);
}
export const Row = ({ children, spread, wrap, style }: { children: ReactNode; spread?: boolean; wrap?: boolean; style?: ViewStyle }) => (
  <View style={[{ flexDirection: 'row', alignItems: 'center', gap: 10, justifyContent: spread ? 'space-between' : 'flex-start', flexWrap: wrap ? 'wrap' : 'nowrap' }, style]}>{children}</View>
);

export function Button({ children, onPress, primary, danger, small, plain, disabled }: { children: ReactNode; onPress?: () => void; primary?: boolean; danger?: boolean; small?: boolean; plain?: boolean; disabled?: boolean }) {
  const c = useTheme();
  const bg = primary ? c.accent : plain ? 'transparent' : c.card;
  const fg = primary ? c.accentInk : danger ? c.bad : c.accent;
  return (<Pressable disabled={disabled} onPress={() => { if (danger) hx.warning(); else if (primary) hx.medium(); else hx.light(); onPress?.(); }} style={({ pressed }) => ({ backgroundColor: bg, opacity: disabled ? 0.45 : pressed ? 0.85 : 1, borderRadius: 16, shadowColor: primary ? c.accent : '#000', shadowOpacity: primary ? 0.35 : 0, shadowRadius: 10, shadowOffset: { width: 0, height: 4 }, elevation: primary ? 4 : 0, paddingVertical: small ? 9 : 15, paddingHorizontal: small ? 14 : 18, alignItems: 'center', marginVertical: small ? 2 : 6, alignSelf: small ? 'flex-start' : 'stretch', transform: [{ scale: pressed ? 0.97 : 1 }] })}>
    <Text style={{ color: fg, fontWeight: '600', fontSize: small ? 15 : 17 }}>{children}</Text></Pressable>);
}
export const Chips = ({ children }: { children: ReactNode }) => <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{children}</View>;
export function Chip({ children, on, onPress }: { children: ReactNode; on?: boolean; onPress: () => void }) {
  const c = useTheme();
  return (<Pressable onPress={() => { haptic(); onPress(); }} style={{ backgroundColor: on ? c.accent : c.card, borderRadius: radius.pill, paddingVertical: 10, paddingHorizontal: 16 }}><Text style={{ color: on ? c.accentInk : c.ink, fontWeight: '500' }}>{children}</Text></Pressable>);
}
export function Pill({ children, tone }: { children: ReactNode; tone?: 'w' | 'b' | 'g' }) {
  const c = useTheme();
  const fg = tone === 'w' ? c.warn : tone === 'b' ? c.bad : tone === 'g' ? c.mut : c.accent;
  return <View style={{ alignSelf: 'flex-start', backgroundColor: fg + '26', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 3 }}><Text style={{ color: fg, fontSize: 13, fontWeight: '600' }}>{children}</Text></View>;
}
export function Segmented({ options, value, onChange }: { options: { key: string; label: string }[]; value: string; onChange: (k: string) => void }) {
  const c = useTheme();
  return (<View style={{ flexDirection: 'row', backgroundColor: c.line, borderRadius: 10, padding: 2, marginVertical: 8 }}>
    {options.map((o) => (<Pressable key={o.key} onPress={() => { haptic(); onChange(o.key); }} style={{ flex: 1, paddingVertical: 8, borderRadius: 8, alignItems: 'center', backgroundColor: o.key === value ? c.card : 'transparent' }}><Text style={{ color: c.ink, fontWeight: '500', fontSize: 14 }}>{o.label}</Text></Pressable>))}</View>);
}
export function Bar({ value }: { value: number }) {
  const c = useTheme(), w = useRef(new Animated.Value(0)).current;
  useEffect(() => { Animated.timing(w, { toValue: Math.max(0.02, Math.min(1, value)), duration: 700, useNativeDriver: false }).start(); }, [value]);
  return <View style={{ height: 8, backgroundColor: c.line, borderRadius: 99, overflow: 'hidden' }}><Animated.View style={{ height: 8, backgroundColor: c.accent, borderRadius: 99, width: w.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] }) }} /></View>;
}

/** Quality score on its 0-100 spectrum: four coloured bands, a marker at the score (the web's ScoreBar). */
export function ScoreBar({ total }: { total: number }) {
  const bands = ['#A33B2B', '#D95A22', '#9CBE77', '#1F4D3A'];
  const pos = Math.max(1, Math.min(99, total));
  return (<View style={{ marginTop: 10 }}>
    <View style={{ flexDirection: 'row', height: 10, borderRadius: 99, overflow: 'visible' }}>
      {bands.map((bg, i) => <View key={i} style={{ flex: 1, backgroundColor: bg, borderTopLeftRadius: i === 0 ? 99 : 0, borderBottomLeftRadius: i === 0 ? 99 : 0, borderTopRightRadius: i === 3 ? 99 : 0, borderBottomRightRadius: i === 3 ? 99 : 0 }} />)}
      <View style={{ position: 'absolute', left: `${pos}%`, top: -3, width: 4, height: 16, borderRadius: 2, backgroundColor: '#fff', borderWidth: 1, borderColor: '#0004' }} />
    </View>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 }}>{['0', '25', '50', '75', '100'].map((n) => <Text key={n} style={{ color: useTheme().mut, fontSize: 11 }}>{n}</Text>)}</View>
  </View>);
}

const TONE_C: Record<string, string> = { g: '#1F4D3A', g2: '#9CBE77', y: '#D95A22', w: '#D95A22', b: '#A33B2B' };
/** An amount placed on its labelled scale: coloured zones from worst to best and a marker at the value (the web's AmountScale). */
export function AmountScale({ scale }: { scale: { value: number; max: number; zones: { from: number; to: number; tone: string }[] } }) {
  const c = useTheme();
  const pos = Math.max(1, Math.min(99, (scale.value / scale.max) * 100));
  return (<View style={{ marginTop: 6 }}>
    <View style={{ flexDirection: 'row', height: 8, borderRadius: 99, overflow: 'visible' }}>
      {scale.zones.map((z, i) => <View key={i} style={{ flex: Math.max(0.0001, z.to - z.from), backgroundColor: TONE_C[z.tone] ?? c.line }} />)}
      <View style={{ position: 'absolute', left: `${pos}%`, top: -3, width: 3, height: 14, borderRadius: 2, backgroundColor: c.ink }} />
    </View>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 3 }}>
      <Text style={{ color: c.mut, fontSize: 11 }}>0</Text>
      <Text style={{ color: c.mut, fontSize: 11 }}>{Math.round(scale.max / 2)}</Text>
      <Text style={{ color: c.mut, fontSize: 11 }}>{scale.max}+</Text>
    </View>
  </View>);
}

const CHAIN_LOOK: Record<string, [string, string, string]> = {
  carrefour: ['#004E9F', '#fff', 'C'], leclerc: ['#0072BC', '#F58220', 'E.L'], intermarche: ['#E2001A', '#fff', 'I'], auchan: ['#E4002B', '#fff', 'A'], lidl: ['#FFD500', '#0050AA', 'Lidl'],
  aldi: ['#00549F', '#fff', 'A'], monoprix: ['#111', '#fff', 'M'], franprix: ['#E2001A', '#fff', 'F'], casino: ['#00A651', '#fff', 'C'], superu: ['#E30613', '#fff', 'U'], picard: ['#0057A8', '#fff', 'P'],
  biocoop: ['#7AB51D', '#fff', 'B'], naturalia: ['#00954F', '#fff', 'N'], lavieclaire: ['#009A44', '#fff', 'VC'], grandfrais: ['#E30613', '#fff', 'GF'], cora: ['#E30613', '#fff', 'C'], match: ['#E30613', '#fff', 'M'],
  walmart: ['#0071CE', '#fff', 'W'], kroger: ['#134A9E', '#fff', 'K'], costco: ['#E31837', '#fff', 'C'], target: ['#CC0000', '#fff', 'T'], albertsons: ['#0066B2', '#fff', 'A'], safeway: ['#E31837', '#fff', 'S'],
};
/** Chain mark: a coloured badge in the chain's colours (the web falls back to the same badge when no logo file exists). */
export function ChainBadge({ id, size = 26 }: { id: string; size?: number }) {
  const [bg, fg, tx] = CHAIN_LOOK[id] ?? ['#888', '#fff', (id[0] ?? '?').toUpperCase()];
  return <View style={{ width: size, height: size, borderRadius: 6, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' }}><Text style={{ color: fg, fontWeight: '800', fontSize: tx.length > 2 ? size * 0.3 : size * 0.44 }}>{tx}</Text></View>;
}

export function CountUp({ value, format }: { value: number; format: (v: number) => string }) {
  const [v, setV] = useState(0), from = useRef(0), ink = useTheme().ink;
  useEffect(() => { const a = from.current, t0 = Date.now(); const id = setInterval(() => { const k = Math.min(1, (Date.now() - t0) / 800), e = 1 - Math.pow(1 - k, 3); setV(a + (value - a) * e); if (k >= 1) { from.current = value; clearInterval(id); } }, 16); return () => clearInterval(id); }, [value]);
  return <Text style={{ color: ink, fontSize: 40, fontWeight: '700', letterSpacing: -1 }}>{format(v)}</Text>;
}
export function NutriScore({ grade }: { grade: string | null }) {
  if (!grade) return null;
  return (<View style={{ flexDirection: 'row', borderRadius: 8, overflow: 'hidden' }}>{['a', 'b', 'c', 'd', 'e'].map((g) => (
    <View key={g} style={{ width: g === grade ? 30 : 22, height: g === grade ? 32 : 26, backgroundColor: nutriScoreColors[g], opacity: g === grade ? 1 : 0.35, alignItems: 'center', justifyContent: 'center' }}><Text style={{ color: '#fff', fontWeight: '800', fontSize: g === grade ? 17 : 13 }}>{g.toUpperCase()}</Text></View>))}</View>);
}
export function NovaBadge({ group, estimated }: { group: number | null | undefined; estimated?: boolean }) {
  if (!group) return <Pill tone="g">NOVA ?</Pill>;
  return <View style={{ alignSelf: 'flex-start', backgroundColor: novaColors[group], borderRadius: 8, paddingHorizontal: 11, paddingVertical: 5 }}><Text style={{ color: '#fff', fontWeight: '800', fontSize: 13 }}>NOVA {group}{estimated ? ' · estimé' : ''}</Text></View>;
}
export function Field(props: { value: string; onChangeText: (s: string) => void; placeholder?: string; numeric?: boolean; multiline?: boolean }) {
  const c = useTheme();
  return <TextInput value={props.value} onChangeText={props.onChangeText} placeholder={props.placeholder} placeholderTextColor={c.mut} keyboardType={props.numeric ? 'decimal-pad' : 'default'} multiline={props.multiline}
    style={{ backgroundColor: c.line, color: c.ink, borderRadius: 12, padding: 12, fontSize: 16, minHeight: props.multiline ? 120 : undefined, textAlignVertical: props.multiline ? 'top' : 'center', marginVertical: 4 }} />;
}
export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title?: string; children: ReactNode }) {
  const c = useTheme();
  return (<Modal visible={open} transparent animationType="slide" onRequestClose={onClose}><Pressable style={{ flex: 1, backgroundColor: '#0006' }} onPress={onClose} />
    <View style={{ backgroundColor: c.bg, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 16, maxHeight: '80%' }}>{title ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700', marginBottom: 8 }}>{title}</Text> : null}<ScrollView>{children}</ScrollView></View></Modal>);
}
export function Toast({ text }: { text: string | null }) {
  if (!text) return null;
  return <View pointerEvents="none" style={{ position: 'absolute', bottom: 40, alignSelf: 'center', backgroundColor: '#1e1e1ee6', borderRadius: 99, paddingHorizontal: 18, paddingVertical: 10 }}><Text style={{ color: '#fff' }}>{text}</Text></View>;
}
export const Skeleton = ({ h = 16 }: { h?: number }) => <View style={{ height: h, borderRadius: 12, backgroundColor: useTheme().line, marginVertical: 8 }} />;

/** The web's Loader: a spinner, a line that advances every 2 s, and a retry after 8 s. */
export function Loader({ steps, label, onRetry }: { steps?: string[]; label?: string; onRetry?: () => void }) {
  const c = useTheme();
  const [i, setI] = useState(0), [slow, setSlow] = useState(false);
  useEffect(() => { if (!steps || steps.length < 2) return; const id = setInterval(() => setI((n) => Math.min(n + 1, steps.length - 1)), 2000); return () => clearInterval(id); }, [steps]);
  useEffect(() => { const id = setTimeout(() => setSlow(true), 8000); return () => clearTimeout(id); }, []);
  return (<View style={{ paddingVertical: 24, alignItems: 'center' }}>
    <ActivityIndicator color={c.accent} />
    <Text style={{ color: c.mut, marginTop: 10 }}>{(steps?.length ? steps[Math.min(i, steps.length - 1)] : label ?? t('common.loading')).replace(/…$/, '')}…</Text>
    {slow && onRetry ? <><Text style={{ color: c.mut, fontSize: 13, marginTop: 8 }}>{t('common.slow')}</Text><Button onPress={onRetry}>{t('common.retry')}</Button></> : null}
  </View>);
}

export function Collapsible({ title, children, open: initial = false }: { title: string; children: ReactNode; open?: boolean }) {
  const c = useTheme();
  const [open, setOpen] = useState(initial);
  return (
    <View style={{ backgroundColor: c.card, borderRadius: radius.md, marginVertical: 6, overflow: 'hidden' }}>
      <Pressable onPress={() => { hx.select(); setOpen(!open); }} style={{ padding: 14, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: c.ink, fontWeight: '600', fontSize: 16, flex: 1, paddingRight: 8 }}>{title}</Text><Text style={{ color: c.mut, fontSize: 20 }}>{open ? '−' : '+'}</Text>
      </Pressable>
      {open ? <View style={{ paddingHorizontal: 14, paddingBottom: 14 }}>{children}</View> : null}
    </View>
  );
}

/** Large friendly header block for the top of a screen. */
export function Hero({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) {
  const c = useTheme();
  return (<View style={{ backgroundColor: c.accent, borderRadius: 24, padding: 20, marginBottom: 12 }}>
    <Text style={{ color: c.accentInk, fontSize: 26, fontWeight: '800', letterSpacing: -0.5 }}>{title}</Text>{sub ? <Text style={{ color: c.accentInk, opacity: 0.85, marginTop: 4, fontSize: 15 }}>{sub}</Text> : null}{children}</View>);
}
