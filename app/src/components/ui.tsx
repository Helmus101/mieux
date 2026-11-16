import { Children, createContext, type ReactNode, useContext, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Easing, LayoutAnimation, Modal, Platform, Pressable, StyleSheet, Text, TextInput, UIManager, View, type PressableProps, type StyleProp, type TextStyle, type ViewStyle } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { BlurView } from 'expo-blur';
import { Image } from 'expo-image';
import * as Haptics from 'expo-haptics';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { t } from '@shared/i18n';
import { nutriScoreColors, novaColors } from '@shared/theme';
import { radius, space, toneColor, useTheme } from '@/lib/theme';
import { LOGOS } from '@/lib/logos';

if (Platform.OS === 'android') UIManager.setLayoutAnimationEnabledExperimental?.(true);

export type HapticKind = 'tap' | 'select' | 'success' | 'warning' | 'error' | 'heavy';
/** Haptics fire on the causal event (press-in, toggle, commit), in step with the visual. */
export const haptic = (k: HapticKind = 'tap') => {
  // Strong by default: medium impact for taps, heavy for the main action, rigid for selections.
  const f = k === 'tap' ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)
    : k === 'heavy' ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy)
    : k === 'select' ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid)
    : Haptics.notificationAsync(k === 'success' ? Haptics.NotificationFeedbackType.Success : k === 'warning' ? Haptics.NotificationFeedbackType.Warning : Haptics.NotificationFeedbackType.Error);
  f.catch(() => undefined);
};
/** Critically damped spring, no overshoot: the default for anything the user touches. */
const spring = (v: Animated.Value, to: number) => Animated.spring(v, { toValue: to, damping: 28, stiffness: 420, mass: 1, useNativeDriver: true }).start();

/** Pressable that responds on press-in (scale .97) and springs back from the live value, so it can be interrupted at any moment. */
export function Press({ children, style, scaleTo = 0.97, onPress, onPressIn, onPressOut, feedback = 'tap', ...rest }: PressableProps & { style?: StyleProp<ViewStyle>; scaleTo?: number; feedback?: HapticKind | null; children: ReactNode }) {
  const v = useRef(new Animated.Value(1)).current;
  return (
    <Pressable {...rest} onPressIn={(e) => { spring(v, scaleTo); onPressIn?.(e); }} onPressOut={(e) => { spring(v, 1); onPressOut?.(e); }}
      onPress={onPress ? (e) => { if (feedback) haptic(feedback); onPress(e); } : undefined}>
      <Animated.View style={[style, { transform: [{ scale: v }] }]}>{children}</Animated.View>
    </Pressable>
  );
}

/** Set while a screen is shown inside the scanner's result sheet: the sheet is already below the status bar, back means "close the sheet",
 * and pulling the content down past its top closes it too. */
export const EmbeddedContext = createContext<{ close: () => void } | null>(null);

/** Page. With `title`, a translucent compact header fades in once the large title scrolls away (content scrolls under it). */
export function Screen({ children, scroll = true, pad = true, bottom = 40, title }: { children: ReactNode; scroll?: boolean; pad?: boolean; bottom?: number; title?: string }) {
  const c = useTheme(), ins = useSafeAreaInsets(), embedded = useContext(EmbeddedContext);
  const y = useRef(new Animated.Value(0)).current;
  const inner = { padding: pad ? space.lg : 0, paddingBottom: embedded ? Math.max(bottom, 120) : bottom, gap: space.md };
  const op = y.interpolate({ inputRange: [24, 56], outputRange: [0, 1], extrapolate: 'clamp' });
  return (
    <SafeAreaView edges={embedded ? [] : ['top']} style={{ flex: 1, backgroundColor: c.bg }}>
      {scroll
        ? <Animated.ScrollView contentContainerStyle={inner} keyboardShouldPersistTaps="handled" contentInsetAdjustmentBehavior="automatic" scrollEventThrottle={16} onScroll={Animated.event([{ nativeEvent: { contentOffset: { y } } }], { useNativeDriver: true })} onScrollEndDrag={embedded ? (e) => { if (e.nativeEvent.contentOffset.y < -70) embedded.close(); } : undefined}>{children}</Animated.ScrollView>
        : <View style={[{ flex: 1 }, inner]}>{children}</View>}
      {scroll && title ? <Animated.View pointerEvents="none" style={[s.compact, { top: 0, height: ins.top + 44, paddingTop: ins.top, opacity: op, borderBottomColor: c.line }]}>
        <BlurView intensity={60} tint="light" style={StyleSheet.absoluteFill} />
        <Text style={{ color: c.ink, fontSize: 17, fontWeight: '600', textAlign: 'center', lineHeight: 44 }}>{title}</Text>
      </Animated.View> : null}
    </SafeAreaView>
  );
}

export function NavBar({ title, right, back = true }: { title?: string; right?: ReactNode; back?: boolean }) {
  const c = useTheme(), r = useRouter(), embedded = useContext(EmbeddedContext);
  return (
    <View style={s.nav}>
      {back ? <Press feedback="tap" scaleTo={0.9} hitSlop={12} onPress={() => { if (embedded) embedded.close(); else if (r.canGoBack()) r.back(); else r.replace('/list'); }} accessibilityLabel={t('common.back')}><Ionicons name="chevron-back" size={28} color={c.accent} /></Press> : <View style={{ width: 12 }} />}
      <Text numberOfLines={1} style={[s.navTitle, { color: c.ink }]}>{title ?? ''}</Text>
      <View style={{ minWidth: 28, alignItems: 'flex-end' }}>{right}</View>
    </View>
  );
}

/** Large title: system weight, tight tracking (large type wants negative tracking). */
export const LargeTitle = ({ children, sub }: { children: ReactNode; sub?: string }) => {
  const c = useTheme();
  return <View style={{ gap: 2 }}><Text style={[s.large, { color: c.ink }]}>{children}</Text>{sub ? <Text style={{ color: c.mut, fontSize: 15 }}>{sub}</Text> : null}</View>;
};
export const H = ({ children, style }: { children: ReactNode; style?: StyleProp<TextStyle> }) => <Text style={[{ color: useTheme().ink, fontSize: 17, fontWeight: '600', letterSpacing: -0.2 }, style]}>{children}</Text>;
export const Body = ({ children, style, bold }: { children: ReactNode; style?: StyleProp<TextStyle>; bold?: boolean }) => <Text style={[{ color: useTheme().ink, fontSize: 17, letterSpacing: -0.2, fontWeight: bold ? '600' : '400' }, style]}>{children}</Text>;
export const Muted = ({ children, style, small }: { children: ReactNode; style?: StyleProp<TextStyle>; small?: boolean }) => <Text style={[{ color: useTheme().mut, fontSize: small ? 13 : 15, letterSpacing: small ? 0 : -0.1 }, style]}>{children}</Text>;

export const Card = ({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) => <View style={[s.card, { backgroundColor: useTheme().card }, style]}>{children}</View>;

/** Pill action, 48 pt high. One filled (primary) action per screen. */
export function Button({ children, onPress, primary, plain, danger, small, disabled }: { children: ReactNode; onPress?: () => void; primary?: boolean; plain?: boolean; danger?: boolean; small?: boolean; disabled?: boolean }) {
  const c = useTheme();
  const bg = primary ? c.accent : plain ? 'transparent' : c.card;
  const fg = primary ? c.accentInk : danger ? c.bad : c.accent;
  return (
    <Press disabled={disabled} feedback={primary ? 'heavy' : 'tap'} onPress={onPress} style={[s.btn, small && { minHeight: 36, paddingHorizontal: 16, alignSelf: 'flex-start' }, { backgroundColor: bg, opacity: disabled ? 0.4 : 1 }]}>
      <Text style={{ color: fg, fontWeight: '600', fontSize: small ? 15 : 17, letterSpacing: -0.2 }}>{children}</Text>
    </Press>
  );
}

/** Tone pills are plain coloured text (as on the web); the default pill is tinted with a hairline. */
export function Pill({ children, tone }: { children: ReactNode; tone?: 'w' | 'b' | 'g' }) {
  const c = useTheme();
  if (tone === 'w' || tone === 'b') return <Text style={{ color: tone === 'b' ? c.bad : c.warn, fontSize: 13, fontWeight: '600' }}>{children}</Text>;
  return <View style={[s.pill, { backgroundColor: c.tint, borderColor: c.line }]}><Text style={{ color: tone === 'g' ? c.mut : c.ink, fontSize: 13, fontWeight: '500' }}>{children}</Text></View>;
}

export const Row = ({ children, spread, wrap, style }: { children: ReactNode; spread?: boolean; wrap?: boolean; style?: StyleProp<ViewStyle> }) =>
  <View style={[{ flexDirection: 'row', alignItems: 'center', gap: 10 }, spread && { justifyContent: 'space-between' }, wrap && { flexWrap: 'wrap' }, style]}>{children}</View>;

export const Section = ({ title, children }: { title?: string; children: ReactNode }) => {
  const c = useTheme();
  return <View style={{ gap: 8 }}>{title ? <Text style={{ color: c.mut, fontSize: 13, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 }}>{title}</Text> : null}{children}</View>;
};

/** Grouped list: hairline above, below and between rows, no card fill (the web's .group). */
export function Group({ children }: { children: ReactNode }) {
  const c = useTheme();
  const kids = Children.toArray(children);
  return (
    <View style={{ borderTopWidth: StyleSheet.hairlineWidth, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: c.line }}>
      {kids.map((k, i) => <View key={i} style={i > 0 ? { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: c.line } : undefined}>{k}</View>)}
    </View>
  );
}

/** List row: optional product image, content, chevron. Highlights on press-in. */
export function Cell({ children, image, chevron, onPress, right }: { children: ReactNode; image?: string | null; chevron?: boolean; onPress?: () => void; right?: ReactNode }) {
  const c = useTheme();
  const inner = (
    <>
      {image !== undefined && <Thumb uri={image} size={52} />}
      <View style={{ flex: 1, gap: 2 }}>{children}</View>
      {right}
      {chevron && <Ionicons name="chevron-forward" size={18} color={c.mut} />}
    </>
  );
  if (!onPress) return <View style={s.cell}>{inner}</View>;
  return <Pressable onPress={() => { haptic('select'); onPress(); }} style={({ pressed }) => [s.cell, pressed && { backgroundColor: c.card }]}>{inner}</Pressable>;
}

export function Thumb({ uri, size = 48 }: { uri?: string | null; size?: number }) {
  const c = useTheme();
  return uri ? <Image source={{ uri }} style={{ width: size, height: size, borderRadius: 8, backgroundColor: '#fff' }} contentFit="contain" transition={150} /> : <View style={{ width: size, height: size, borderRadius: 8, backgroundColor: c.tint }} />;
}

/** Segmented control with a thumb that springs between options. */
export function Segmented({ value, onChange, options }: { value: string; onChange: (k: string) => void; options: { key: string; label: string }[] }) {
  const c = useTheme();
  const [w, setW] = useState(0);
  const idx = Math.max(0, options.findIndex((o) => o.key === value)), x = useRef(new Animated.Value(idx)).current;
  useEffect(() => { Animated.spring(x, { toValue: idx, damping: 26, stiffness: 320, mass: 1, useNativeDriver: true }).start(); }, [idx, x]);
  const iw = w ? (w - 4) / options.length : 0;
  return (
    <View style={[s.seg, { backgroundColor: c.card }]} onLayout={(e) => setW(e.nativeEvent.layout.width)}>
      {iw > 0 && <Animated.View style={[s.thumb, { width: iw, backgroundColor: c.dark ? '#2A332E' : '#fff', transform: [{ translateX: x.interpolate({ inputRange: options.map((_, i) => i), outputRange: options.map((_, i) => i * iw) }) }] }]} />}
      {options.map((o) => (
        <Pressable key={o.key} onPress={() => { if (o.key !== value) { haptic('select'); onChange(o.key); } }} style={s.segItem}>
          <Text style={{ color: o.key === value ? c.ink : c.mut, fontWeight: o.key === value ? '600' : '500', fontSize: 15 }}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export const Chips = ({ children }: { children: ReactNode }) => <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>{children}</View>;
export function Chip({ children, on, onPress }: { children: ReactNode; on?: boolean; onPress?: () => void }) {
  const c = useTheme();
  return <Press feedback="select" scaleTo={0.95} onPress={onPress} style={[s.chip, { borderColor: on ? c.accent : c.line, backgroundColor: on ? c.accent : 'transparent' }]}><Text style={{ color: on ? c.accentInk : c.ink, fontWeight: '500', fontSize: 15 }}>{children}</Text></Press>;
}

/** Tinted field, 12 pt radius, accent ring on focus. */
export function Field(props: React.ComponentProps<typeof TextInput>) {
  const c = useTheme();
  const [focus, setFocus] = useState(false);
  return <TextInput placeholderTextColor={c.mut} {...props} onFocus={(e) => { setFocus(true); props.onFocus?.(e); }} onBlur={(e) => { setFocus(false); props.onBlur?.(e); }}
    style={[s.input, { backgroundColor: c.card, color: c.ink, borderColor: focus ? c.accent : 'transparent' }, props.style]} />;
}

/** Horizontal bar, value 0..1, coloured by tone. */
export function Bar({ value, tone }: { value: number; tone?: string }) {
  const c = useTheme();
  return <View style={{ height: 6, borderRadius: 3, backgroundColor: c.line, overflow: 'hidden' }}><View style={{ height: 6, width: `${Math.max(2, Math.min(1, value) * 100)}%`, backgroundColor: tone ? toneColor(tone, c.dark) : c.accent, borderRadius: 3 }} /></View>;
}

/** Disclosure row: lives inside a <Group>, so rows share hairlines instead of being separate cards. */
export function Collapsible({ title, children, open: init = false }: { title: string; children: ReactNode; open?: boolean }) {
  const c = useTheme();
  const [open, setOpen] = useState(init);
  const rot = useRef(new Animated.Value(init ? 1 : 0)).current;
  const toggle = () => {
    haptic('select');
    LayoutAnimation.configureNext({ duration: 260, update: { type: 'easeInEaseOut' }, create: { type: 'easeInEaseOut', property: 'opacity' }, delete: { type: 'easeInEaseOut', property: 'opacity' } });
    Animated.timing(rot, { toValue: open ? 0 : 1, duration: 220, easing: Easing.bezier(0.32, 0.72, 0, 1), useNativeDriver: true }).start();
    setOpen(!open);
  };
  return (
    <View style={{ paddingVertical: 4 }}>
      <Pressable onPress={toggle} style={({ pressed }) => [{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, minHeight: 48 }, pressed && { opacity: 0.6 }]}>
        <Text style={{ color: c.ink, fontSize: 17, fontWeight: '600', flex: 1, paddingRight: 8, letterSpacing: -0.2 }}>{title}</Text>
        <Animated.View style={{ transform: [{ rotate: rot.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '90deg'] }) }] }}><Ionicons name="chevron-forward" size={18} color={c.mut} /></Animated.View>
      </Pressable>
      {open && <View style={{ paddingBottom: 12, gap: 4 }}>{children}</View>}
    </View>
  );
}

/** Bottom sheet: scrim, grabber, material surface. */
export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title?: string; children: ReactNode }) {
  const c = useTheme();
  useEffect(() => { if (open) haptic('tap'); }, [open]);
  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.35)' }} onPress={onClose} />
      <View style={[s.sheet, { backgroundColor: c.bg }]}>
        <View style={{ alignSelf: 'center', width: 36, height: 5, borderRadius: 3, backgroundColor: c.line, marginBottom: 12 }} />
        {title ? <Text style={{ color: c.ink, fontSize: 22, fontWeight: '700', letterSpacing: -0.4, marginBottom: 8 }}>{title}</Text> : null}
        <Animated.ScrollView contentContainerStyle={{ gap: 10, paddingBottom: 28 }}>{children}</Animated.ScrollView>
      </View>
    </Modal>
  );
}

export function Confirm({ open, onClose, onConfirm, title, action, children }: { open: boolean; onClose: () => void; onConfirm: () => void; title: string; action: string; children?: ReactNode }) {
  return (
    <Sheet open={open} onClose={onClose} title={title}>
      {typeof children === 'string' ? <Muted>{children}</Muted> : children}
      <Button danger onPress={() => { haptic('warning'); onConfirm(); onClose(); }}>{action}</Button>
      <Button plain onPress={onClose}>{t('common.cancel')}</Button>
    </Sheet>
  );
}

/** Spinner with rotating status lines (and a retry link when it takes long). */
export function Loader({ steps, onRetry, slowAfter = 20000 }: { steps?: string[]; onRetry?: () => void; slowAfter?: number }) {
  const c = useTheme();
  const [i, setI] = useState(0), [slow, setSlow] = useState(false);
  useEffect(() => {
    const a = setInterval(() => setI((n) => n + 1), 1600), b = setTimeout(() => setSlow(true), slowAfter);
    return () => { clearInterval(a); clearTimeout(b); };
  }, [slowAfter]);
  const lines = steps?.length ? steps : [t('common.loading')];
  return (
    <View style={{ alignItems: 'center', gap: 10, paddingVertical: 24 }}>
      <ActivityIndicator color={c.accent} />
      <Muted>{lines[Math.min(i, lines.length - 1)]}</Muted>
      {slow && <><Muted small>{t('common.slow')}</Muted>{onRetry && <Button small plain onPress={onRetry}>{t('common.retry')}</Button>}</>}
    </View>
  );
}

export function Skeleton({ h = 16, w = '100%' }: { h?: number; w?: number | `${number}%` }) {
  const c = useTheme(), o = useRef(new Animated.Value(0.4)).current;
  useEffect(() => { const a = Animated.loop(Animated.sequence([Animated.timing(o, { toValue: 1, duration: 700, useNativeDriver: true }), Animated.timing(o, { toValue: 0.4, duration: 700, useNativeDriver: true })])); a.start(); return () => a.stop(); }, [o]);
  return <Animated.View style={{ height: h, width: w, borderRadius: 8, backgroundColor: c.line, opacity: o }} />;
}

export const NutriScore = ({ grade }: { grade?: string | null }) => {
  const g = (grade ?? '').toLowerCase();
  return g in nutriScoreColors ? <View style={[s.badge, { backgroundColor: nutriScoreColors[g] }]}><Text style={s.badgeTxt}>{g.toUpperCase()}</Text></View> : <Text>—</Text>;
};
export const NovaBadge = ({ group }: { group?: number | null }) =>
  group && novaColors[group] ? <View style={[s.badge, { backgroundColor: novaColors[group] }]}><Text style={s.badgeTxt}>{group}</Text></View> : <Text>—</Text>;

/** Score numeral set in the tone colour (no filled badge: filled tiles read as alarms), tabular figures. */
export const ScoreTile = ({ value, tone }: { value: number | string; tone?: string }) => {
  const c = useTheme();
  return <View style={{ flexDirection: 'row', alignItems: 'baseline' }}><Text style={{ color: toneColor(tone, c.dark), fontSize: 44, fontWeight: '700', letterSpacing: -1.5, fontVariant: ['tabular-nums'] }}>{value}</Text><Text style={{ color: c.mut, fontSize: 15, fontWeight: '500' }}>{t('score.outOf')}</Text></View>;
};

export const Brand = ({ size = 22 }: { size?: number }) => <Text style={{ color: useTheme().accent, fontSize: size, fontWeight: '800', letterSpacing: -size * 0.04 }}>mieux.</Text>;

/** Store logo (image from the web app's logo set); a coloured initial only when a chain has no logo file. */
export function ChainLogo({ id, name, size = 28 }: { id?: string; name: string; size?: number }) {
  const c = useTheme();
  const src = id ? LOGOS[id] : undefined;
  if (src) return <Image source={src} accessibilityLabel={name} style={{ width: size, height: size, borderRadius: 8, backgroundColor: '#fff' }} contentFit="contain" />;
  return <View accessibilityLabel={name} style={{ width: size, height: size, borderRadius: 8, backgroundColor: c.tint, alignItems: 'center', justifyContent: 'center' }}><Text style={{ color: c.accent, fontWeight: '700', fontSize: size * 0.45 }}>{name.charAt(0)}</Text></View>;
}

export function Toast({ text }: { text: string | null }) {
  const c = useTheme();
  if (!text) return null;
  return <View style={{ position: 'absolute', bottom: 16, left: 16, right: 16, backgroundColor: c.ink, padding: 12, borderRadius: radius.md }}><Text style={{ color: c.bg }}>{text}</Text></View>;
}

const s = StyleSheet.create({
  compact: { position: 'absolute', left: 0, right: 0, borderBottomWidth: StyleSheet.hairlineWidth, overflow: 'hidden' },
  nav: { flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 36 },
  navTitle: { flex: 1, fontSize: 17, fontWeight: '600', textAlign: 'center', letterSpacing: -0.2 },
  large: { fontSize: 34, fontWeight: '700', letterSpacing: -0.9, lineHeight: 40 },
  card: { borderRadius: 16, padding: 16, gap: 6 },
  btn: { borderRadius: 999, minHeight: 48, paddingHorizontal: 22, alignItems: 'center', justifyContent: 'center' },
  pill: { borderRadius: 999, borderWidth: StyleSheet.hairlineWidth, paddingHorizontal: 12, paddingVertical: 5, alignSelf: 'flex-start' },
  cell: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 12, paddingHorizontal: 2, minHeight: 52 },
  seg: { flexDirection: 'row', borderRadius: 12, padding: 2 },
  thumb: { position: 'absolute', top: 2, bottom: 2, left: 2, borderRadius: 10, shadowColor: '#000', shadowOpacity: 0.14, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 2 },
  segItem: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center' },
  chip: { borderWidth: 1, borderRadius: 999, minHeight: 40, paddingHorizontal: 16, alignItems: 'center', justifyContent: 'center' },
  input: { borderRadius: 12, borderWidth: 2, paddingHorizontal: 14, paddingVertical: 12, fontSize: 17, minHeight: 48 },
  sheet: { maxHeight: '85%', borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: space.lg, paddingTop: 10 },
  badge: { width: 28, height: 28, borderRadius: 6, alignItems: 'center', justifyContent: 'center' },
  badgeTxt: { color: '#fff', fontWeight: '800' },
});
