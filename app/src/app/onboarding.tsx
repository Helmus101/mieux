import { useRef, useState } from 'react';
import { Animated, Dimensions, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { api } from '@shared/api/client';
import { setLocale } from '@shared/i18n';
import { useProfile } from '@shared/stores';
import { Brand, Button, Segmented, haptic } from '@/components/ui';
import { useTheme } from '@/lib/theme';

type Slide = { icon: keyof typeof Ionicons.glyphMap; quote: string; who: string; title: string; text: string };
const COPY: Record<'fr' | 'en', { skip: string; next: string; start: string; slides: Slide[] }> = {
  fr: {
    skip: 'Passer', next: 'Suivant', start: 'Scanner mon premier produit',
    slides: [
      { icon: 'help-circle-outline', quote: '« Je lis l’étiquette… et je n’y comprends rien. »', who: 'Tout le monde, au rayon yaourts', title: 'Manger mieux, sans devenir expert', text: 'Des listes d’ingrédients interminables, des noms de code, des promesses « sain » en gros sur l’emballage. Mieux les traduit pour vous.' },
      { icon: 'scan-outline', quote: '« Pourquoi y a-t-il du E471 dans mon yaourt ? »', who: 'Une question qu’on s’est tous posée', title: 'Scannez, comprenez en 2 secondes', text: 'Un score sur 100, les additifs expliqués en mots simples, et ce qui pose vraiment problème : sucre, sel, ultra-transformation.' },
      { icon: 'swap-horizontal-outline', quote: '« Le moins cher… mais est-ce que c’est bon ? »', who: 'Le dilemme de chaque passage en caisse', title: 'Meilleur ET moins cher', text: 'Mieux propose des alternatives de la même catégorie, vendues près de chez vous, avec le prix au kilo et la différence en euros.' },
      { icon: 'lock-closed-outline', quote: '« Je veux savoir ce que je mange, pas qu’on me suive. »', who: 'Vous, sûrement', title: 'Vos données restent sur votre téléphone', text: 'Pas de compte, pas de pub. Vos allergies sont des exclusions strictes, et quand une donnée manque, on vous le dit : inconnu n’est jamais « sûr ».' },
    ],
  },
  en: {
    skip: 'Skip', next: 'Next', start: 'Scan my first product',
    slides: [
      { icon: 'help-circle-outline', quote: '“I read the label… and understand nothing.”', who: 'Everyone, in the yogurt aisle', title: 'Eat better without becoming an expert', text: 'Endless ingredient lists, code names, “healthy” promises in big letters. Mieux translates them for you.' },
      { icon: 'scan-outline', quote: '“Why is there E471 in my yogurt?”', who: 'A question we have all asked', title: 'Scan, understand in 2 seconds', text: 'A score out of 100, additives explained in plain words, and what really matters: sugar, salt, ultra-processing.' },
      { icon: 'swap-horizontal-outline', quote: '“Cheapest… but is it any good?”', who: 'The dilemma at every checkout', title: 'Better AND cheaper', text: 'Mieux suggests same-category alternatives sold near you, with the price per kilo and the difference in euros.' },
      { icon: 'lock-closed-outline', quote: '“I want to know what I eat, not be tracked.”', who: 'You, probably', title: 'Your data stays on your phone', text: 'No account, no ads. Allergies are hard exclusions, and when data is missing we say so: unknown never means “safe”.' },
    ],
  },
};

/** Four short swipeable screens: the problem in the user's own words, then what Mieux does about it. */
export default function Onboarding() {
  const p = useProfile(), c = useTheme();
  const lang = (p.language ?? 'fr') as 'fr' | 'en', copy = COPY[lang];
  const W = Dimensions.get('window').width;
  const x = useRef(new Animated.Value(0)).current, list = useRef<{ scrollTo: (o: { x: number; animated: boolean }) => void } | null>(null);
  const [i, setI] = useState(0);
  const last = i === copy.slides.length - 1;
  const go = (n: number) => { setI(n); haptic("select"); list.current?.scrollTo({ x: n * W, animated: true }); };
  const finish = () => { haptic('success'); if (!p.priorities.length) p.setPriorities(['value']); p.finish(); void api.countOnboarding(); };
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: c.bg }}>
      <View style={{ paddingHorizontal: 20, paddingTop: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <Brand size={26} />
        <View style={{ width: 170 }}><Segmented value={lang} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k); }} options={[{ key: 'fr', label: 'FR' }, { key: 'en', label: 'EN' }]} /></View>
      </View>
      <Animated.ScrollView ref={list as never} horizontal pagingEnabled showsHorizontalScrollIndicator={false} scrollEventThrottle={16}
        onScroll={Animated.event([{ nativeEvent: { contentOffset: { x } } }], { useNativeDriver: true })}
        onMomentumScrollEnd={(e) => { const n = Math.round(e.nativeEvent.contentOffset.x / W); if (n !== i) { setI(n); haptic('select'); } }}>
        {copy.slides.map((sl, n) => {
          const sc = x.interpolate({ inputRange: [(n - 1) * W, n * W, (n + 1) * W], outputRange: [0.9, 1, 0.9], extrapolate: 'clamp' });
          const op = x.interpolate({ inputRange: [(n - 1) * W, n * W, (n + 1) * W], outputRange: [0, 1, 0], extrapolate: 'clamp' });
          return (
            <View key={n} style={{ width: W, paddingHorizontal: 28, justifyContent: 'center', gap: 18 }}>
              <Animated.View style={{ opacity: op, transform: [{ scale: sc }], gap: 18 }}>
                <View style={{ width: 72, height: 72, borderRadius: 22, backgroundColor: c.tint, alignItems: 'center', justifyContent: 'center' }}><Ionicons name={sl.icon} size={38} color={c.accent} /></View>
                <View style={{ backgroundColor: c.card, borderRadius: 20, padding: 20, gap: 8 }}>
                  <Text style={{ color: c.ink, fontSize: 22, fontWeight: '600', lineHeight: 29, letterSpacing: -0.4 }}>{sl.quote}</Text>
                  <Text style={{ color: c.mut, fontSize: 14 }}>— {sl.who}</Text>
                </View>
                <Text style={{ color: c.ink, fontSize: 32, fontWeight: '700', letterSpacing: -0.9, lineHeight: 37 }}>{sl.title}</Text>
                <Text style={{ color: c.mut, fontSize: 17, lineHeight: 24 }}>{sl.text}</Text>
              </Animated.View>
            </View>
          );
        })}
      </Animated.ScrollView>
      <View style={{ paddingHorizontal: 20, paddingBottom: 12, gap: 14 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 8 }}>
          {copy.slides.map((_, n) => <Animated.View key={n} style={{ height: 8, borderRadius: 4, backgroundColor: c.accent, width: x.interpolate({ inputRange: [(n - 1) * W, n * W, (n + 1) * W], outputRange: [8, 24, 8], extrapolate: 'clamp' }), opacity: x.interpolate({ inputRange: [(n - 1) * W, n * W, (n + 1) * W], outputRange: [0.25, 1, 0.25], extrapolate: 'clamp' }) }} />)}
        </View>
        <Button primary onPress={last ? finish : () => go(i + 1)}>{last ? copy.start : copy.next}</Button>
        <View style={{ minHeight: 36 }}>{!last && <Button plain onPress={finish}>{copy.skip}</Button>}</View>
      </View>
    </SafeAreaView>
  );
}
