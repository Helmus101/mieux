/** React Native implementation of the same primitives as web/src/ui/index.tsx. Screens only import from here. */
import { ReactNode, useEffect, useRef, useState } from 'react';
import { Animated, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View, useColorScheme, ViewStyle } from 'react-native';
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
export function Cell({ children, onPress, last }: { children: ReactNode; onPress?: () => void; last?: boolean }) {
  const c = useTheme();
  return (<Pressable onPress={onPress ? () => { hx.light(); onPress(); } : undefined} style={({ pressed }) => ({ padding: 14, minHeight: 48, justifyContent: 'center', backgroundColor: pressed && onPress ? c.line : 'transparent', borderBottomWidth: last ? 0 : StyleSheet.hairlineWidth, borderBottomColor: c.line })}>{children}</Pressable>);
}
export const Row = ({ children, spread, wrap, style }: { children: ReactNode; spread?: boolean; wrap?: boolean; style?: ViewStyle }) => (
  <View style={[{ flexDirection: 'row', alignItems: 'center', gap: 10, justifyContent: spread ? 'space-between' : 'flex-start', flexWrap: wrap ? 'wrap' : 'nowrap' }, style]}>{children}</View>);

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

export function Collapsible({ title, children, open: initial = false }: { title: string; children: ReactNode; open?: boolean }) {
  const c = useTheme();
  const [open, setOpen] = useState(initial);
  return (
    <View style={{ backgroundColor: c.card, borderRadius: radius.md, marginVertical: 6, overflow: 'hidden' }}>
      <Pressable onPress={() => { hx.select(); setOpen(!open); }} style={{ padding: 14, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: c.ink, fontWeight: '600', fontSize: 16 }}>{title}</Text><Text style={{ color: c.mut, fontSize: 20 }}>{open ? '−' : '+'}</Text>
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
