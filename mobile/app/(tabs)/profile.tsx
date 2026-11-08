import { useState } from 'react';
import { Alert, Linking, Pressable, ScrollView, Share, Text, View } from 'react-native';
import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { clearAll } from '@shared/storage';
import { useProfile, useHistory } from '@shared/stores';
import { chainsFor, COUNTRIES, type Country } from '@shared/chains';
import { Button, Brand, Card, Cell, ChainBadge, Chip, Chips, Collapsible, Field, Group, LargeTitle, Muted, NavBar, Pill, Row, Screen, Section, Segmented, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import * as hx from '../../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const EMAIL = 'bonjourmieuxmanger@gmail.com';

/** Profile: the same sections in the same order as the web screen (location, language, market, chains, diet, restrictions, contact, local data). */
export default function Profile() {
  const c = useTheme();
  const p = useProfile();
  const { go } = useNav();
  const hist = useHistory();
  const [q, setQ] = useState(''), [sugg, setSugg] = useState<any[]>([]);

  const type = async (v: string) => {
    setQ(v);
    if (v.trim().length < 3) { setSugg([]); return; }
    try { setSugg((await api.searchAddress(v)) ?? []); } catch { setSugg([]); }
  };
  const exp = async () => {
    const d = { server: await api.exportData().catch(() => null), device: hist.exportAll(), zone: p.zone };
    await Share.share({ message: JSON.stringify(d, null, 1), title: 'mieux-donnees.json' }).catch(() => undefined);
  };
  const erase = () => Alert.alert(t('profile.eraseConfirm'), '', [{ text: t('common.cancel') }, {
    text: t('profile.erase'), style: 'destructive', onPress: async () => {
      hx.heavy(); await api.deleteAccount().catch(() => undefined); hist.clear(); clearAll(); p.reset();
    },
  }]);

  return (
    <Screen>
      <NavBar title={t('profile.title')} />
      <LargeTitle>{t('profile.title')}</LargeTitle>

      <Section title={t('simple.loc')}>
        <Muted small>{t('about.name')}</Muted>
        <Field value={p.name ?? ''} onChangeText={p.setName} placeholder={t('about.namePh')} />
        <Field value={q} onChangeText={type} placeholder={p.place ? (p.place.label ?? ([p.place.city, p.place.postcode].filter(Boolean).join(' · ') || t('about.addrPh'))) : t('about.addrPh')} />
        {sugg.length > 0 ? <Group>{sugg.map((a, i) => (
          <Cell key={a.label} last={i === sugg.length - 1} onPress={() => { p.setPlace(a); setQ(''); setSugg([]); }}>
            <Text style={{ color: c.ink }}>{a.label}</Text>
          </Cell>))}</Group> : null}
        <Muted small>{t('about.homeHint')}</Muted>
      </Section>

      <Section title={t('profile.language')}>
        <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      </Section>

      {COUNTRIES.length > 1 ? <Section title={t('profile.country')}>
        <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((x) => ({ key: x, label: t('country.' + x) }))} />
        {p.country === 'US' ? <Muted small>{t('country.usNote')}</Muted> : null}
      </Section> : null}

      <Collapsible title={t('chains.title')}>
        <Muted small>{t('chains.hint')}</Muted>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {chainsFor(p.country).map((ch) => {
            const on = (p.chains ?? []).includes(ch.id);
            return (
              <Pressable key={ch.id} onPress={() => { hx.select(); p.toggleChain(ch.id); }} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8, paddingHorizontal: 12, borderRadius: 999, backgroundColor: on ? c.accent : c.bg, borderWidth: 1, borderColor: on ? c.accent : c.line }}>
                <ChainBadge id={ch.id} size={20} />
                <Text style={{ color: on ? c.accentInk : c.ink, fontWeight: '500' }}>{ch.name}</Text>
              </Pressable>);
          })}
        </View>
        <Muted small style={{ marginTop: 8 }}>{(p.chains ?? []).length ? t('chains.some', { n: (p.chains ?? []).length }) : t('chains.all')}
          {(p.chains ?? []).length > 0 ? <Text onPress={() => p.clearChains()} style={{ color: c.accent }}> · {t('chains.clear')}</Text> : null}
        </Muted>
      </Collapsible>

      <Section title={t('profile.diet')}><Segmented value={p.diet} onChange={(k) => p.setDiet(k as any)} options={(['omnivore', 'vegetarian', 'vegan'] as const).map((d) => ({ key: d, label: t('diets.' + d) }))} /></Section>
      <Section title={t('profile.restrictions')}>
        <Chips>{['gluten', 'milk', 'peanuts', 'nuts'].map((a) => <Chip key={a} on={p.allergens.includes(a)} onPress={() => p.toggleAllergen(a)}>{t('diets.' + a)}</Chip>)}</Chips>
        <Muted small>{t('onboarding.allergyNote')}</Muted>
      </Section>

      <Section title={t('profile.contactTitle')}>
        <Group>
          <Cell last chevron onPress={() => { Linking.openURL(`mailto:${EMAIL}?subject=${encodeURIComponent(t('profile.contactSubject'))}`).catch(() => undefined); }}>
            <Text style={{ color: c.ink }}>{t('profile.contact')}</Text>
            <Muted small>{t('profile.contactSub')} · {EMAIL}</Muted>
          </Cell>
        </Group>
      </Section>

      <Section title={t('profile.localTitle')}>
        <Group>
          <Cell chevron onPress={() => go(routes.list)}><Text style={{ color: c.ink }}>{t('list.open')}</Text></Cell>
          <Cell chevron onPress={() => go(routes.history)}><Text style={{ color: c.ink }}>{t('history.open')}</Text></Cell>
          <Cell chevron onPress={exp}><Text style={{ color: c.ink }}>{t('profile.export')}</Text></Cell>
          <Cell last onPress={erase}><Text style={{ color: c.bad }}>{t('profile.erase')}</Text></Cell>
        </Group>
      </Section>

      <View style={{ alignItems: 'center', marginTop: 26 }}>
        <Brand size={30} />
        <Text style={{ color: c.mut, marginTop: 8 }}>{t('brand.tagline')}</Text>
        <Text style={{ color: c.mut, fontSize: 13 }}>{t('brand.credit')}</Text>
      </View>
    </Screen>
  );
}
