import { useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import * as Location from 'expo-location';
import { t } from '@shared/i18n';
import { useProfile, PRIORITY_KEYS } from '@shared/stores';
import * as hx from './haptics';
import { Button, Card, Field, LargeTitle, Muted, Pill, Screen, useTheme } from './ui';

const DIET: [string, string][] = [['omnivore', 'diet'], ['vegetarian', 'diet'], ['vegan', 'diet'], ['gluten', 'allergen'], ['milk', 'allergen'], ['peanuts', 'allergen'], ['nuts', 'allergen']];

function Opt({ on, label, onPress, disabled }: { on: boolean; label: string; onPress: () => void; disabled?: boolean }) {
  const c = useTheme();
  return (<Pressable disabled={disabled} onPress={() => { hx.select(); onPress(); }} style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: on ? c.tint : c.card, borderRadius: 16, padding: 16, marginVertical: 5, borderWidth: 2, borderColor: on ? c.accent : 'transparent', opacity: disabled ? 0.5 : 1 }}>
    <Text style={{ color: c.ink, fontWeight: '600', flex: 1 }}>{label}</Text><View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: on ? c.accent : 'transparent', borderWidth: 2, borderColor: on ? c.accent : c.line }} /></Pressable>);
}

/** Approximate city via the iPhone's location services (Apple's geocoder on iOS). Coordinates are used once and discarded. */
export async function findCity(): Promise<{ city: string; postcode: string | null } | 'denied' | null> {
  const perm = await Location.requestForegroundPermissionsAsync();
  if (perm.status !== 'granted') return 'denied';
  const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low });
  const [a] = await Location.reverseGeocodeAsync({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
  const city = a?.city ?? a?.subregion ?? a?.region ?? null;
  return city ? { city, postcode: a?.postalCode ?? null } : null;
}

export default function Onboarding() {
  const p = useProfile();
  const c = useTheme();
  const [step, setStep] = useState(-1);
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState('');
  const locate = async () => {
    setBusy(true); setMsg('');
    try { const r = await findCity(); if (r === 'denied') { setMsg(t('about.locDenied')); hx.warning(); } else if (!r) { setMsg(t('about.locFail')); hx.error(); } else { p.setPlace(r); hx.success(); } }
    catch { setMsg(t('about.locFail')); hx.error(); } finally { setBusy(false); }
  };
  if (step === -1) return (<Screen scroll={false}><View style={{ flex: 1, justifyContent: 'center' }}><LargeTitle kicker="FOODIQ" sub={t('welcome.sub')}>{t('welcome.title')}</LargeTitle></View>
    <Button primary onPress={() => setStep(0)}>{t('welcome.start')}</Button><Button plain onPress={() => p.finish()}>{t('welcome.guest')}</Button></Screen>);
  return (
    <Screen>
      <View style={{ flexDirection: 'row', gap: 6, justifyContent: 'center', marginBottom: 12 }}>{[0, 1, 2].map((i) => <View key={i} style={{ height: 6, width: step === i ? 22 : 6, borderRadius: 3, backgroundColor: step === i ? c.accent : c.line }} />)}</View>
      {step === 0 && <>
        <LargeTitle sub={t('about.sub')}>{t('about.title')}</LargeTitle>
        <Muted>{t('about.name')}</Muted><Field value={p.name ?? ''} onChangeText={p.setName} placeholder={t('about.namePh')} />
        <Card>
          <Text style={{ color: c.ink, fontWeight: '700', fontSize: 17 }}>{t('about.locTitle')}</Text>
          {p.place ? <View style={{ marginVertical: 8 }}><Pill>{[p.place.city, p.place.postcode].filter(Boolean).join(' · ')}</Pill></View> : <Muted small>{t('about.locHint')}</Muted>}
          {busy ? <ActivityIndicator style={{ margin: 12 }} /> : <Button onPress={locate}>{p.place ? t('about.change') : t('about.locBtn')}</Button>}
          {msg ? <Text style={{ color: c.warn }}>{msg}</Text> : null}
          {p.place ? <Button small plain danger onPress={() => p.setPlace(null)}>{t('about.clear')}</Button> : null}
        </Card>
        <Button primary onPress={() => setStep(1)}>{t('common.continue')}</Button><Button plain onPress={() => setStep(1)}>{t('common.skip')}</Button></>}
      {step === 1 && <><LargeTitle sub={`${t('onboarding.s1')} · ${t('onboarding.selected', { n: p.priorities.length })}`}>{t('onboarding.t1')}</LargeTitle>
        {[...PRIORITY_KEYS, 'eco'].map((k) => <Opt key={k} on={p.priorities.includes(k)} label={t('priorities.' + k)} disabled={k === 'eco'} onPress={() => p.togglePriority(k)} />)}
        <Button primary onPress={() => setStep(2)}>{t('common.continue')}</Button><Button plain onPress={() => setStep(0)}>{t('common.back')}</Button></>}
      {step === 2 && <><LargeTitle sub={t('onboarding.s2')}>{t('onboarding.t2')}</LargeTitle>
        {DIET.map(([k, kind]) => <Opt key={k} on={kind === 'diet' ? p.diet === k : p.allergens.includes(k)} label={t('diets.' + k)} onPress={() => (kind === 'diet' ? p.setDiet(k as never) : p.toggleAllergen(k))} />)}
        <Muted small>{t('onboarding.allergyNote')}</Muted>
        <Button primary onPress={() => { hx.success(); p.finish(); }}>{t('onboarding.start')}</Button><Button plain onPress={() => setStep(1)}>{t('common.back')}</Button></>}
    </Screen>
  );
}
