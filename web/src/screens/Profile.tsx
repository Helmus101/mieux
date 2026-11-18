import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { clearAll } from '@shared/storage';
import { wipeLocalData } from '../wipe';
import { countingOff, setCounting } from '../usage';
import { NewsModal, newsState } from '../NewsSignup';
import { useProfile, useHistory } from '@shared/stores';
import { useState } from 'react';
import { Screen, NavBar, LargeTitle, Section, Chips, Chip, Group, Cell, Segmented, Confirm } from '../ui';
import { COUNTRIES, type Country } from '@shared/chains';
import { searchAddress, type Home } from '../place';
import { isInstalled, openInstall } from '../install';
import { APP_VERSION } from '../report';

export default function Profile() {
  const p = useProfile();
  const hist = useHistory();
  const [, setTick] = useState(0);
  const [q, setQ] = useState(''), [sugg, setSugg] = useState<Home[]>([]);
  const type = async (v: string) => { setQ(v); setSugg(await searchAddress(v)); };
  const exp = async () => { const d = { server: await api.exportData().catch(() => null), device: hist.exportAll(), zone: p.zone }; const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 1)], { type: 'application/json' })); a.download = 'mieux-donnees.json'; a.click(); };
  const [askErase, setAskErase] = useState(false), [news, setNews] = useState(false);
  const erase = async () => { await api.deleteAccount().catch(() => undefined); hist.clear(); clearAll(); p.reset(); await wipeLocalData(); location.href = '/'; };
  return (
    <Screen>
      <NavBar />
      <LargeTitle>{t('profile.title')}</LargeTitle>
      <Section title={t('simple.loc')}>
        <input value={p.name ?? ''} onChange={(e) => p.setName(e.target.value)} placeholder={t('about.namePh')} autoComplete="given-name" />
        <input value={q} onChange={(e) => type(e.target.value)} placeholder={p.place ? (p.place.label ?? ([p.place.city, p.place.postcode].filter(Boolean).join(' · ') || t('about.addrPh'))) : t('about.addrPh')} autoComplete="street-address" style={{ marginTop: 12 }} />
        {sugg.map((a) => <Cell key={a.label} onPress={() => { p.setPlace(a); setQ(''); setSugg([]); }}>{a.label}</Cell>)}
        <p className="mut sm">{t('about.homeHint')}</p>
      </Section>
      <Section title={t('profile.language')}>
        <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k as 'fr' | 'en'); setTick((n) => n + 1); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      </Section>
      {COUNTRIES.length > 1 && <Section title={t('profile.country')}>
        {COUNTRIES.length > 1 && <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((c) => ({ key: c, label: t('country.' + c) }))} />}
        {p.country === 'US' && <p className="mut sm">{t('country.usNote')}</p>}
      </Section>}
      <Section title={t('profile.diet')}><Segmented value={p.diet} onChange={(k) => p.setDiet(k as 'omnivore' | 'vegetarian' | 'vegan')} options={(['omnivore', 'vegetarian', 'vegan'] as const).map((d) => ({ key: d, label: t('diets.' + d) }))} /></Section>
      <Section title={t('profile.restrictions')}><Chips>{['gluten', 'milk', 'peanuts', 'nuts'].map((a) => <Chip key={a} on={p.allergens.includes(a)} onPress={() => p.toggleAllergen(a)}>{t('diets.' + a)}</Chip>)}</Chips><p className="mut sm">{t('onboarding.allergyNote')}</p></Section>
      <Section title={t('profile.contactTitle')}>
        <Group>
          {!isInstalled() && <Cell onPress={openInstall} chevron>{t('pwa.profile')}</Cell>}
          <Cell onPress={() => { window.location.href = `mailto:bonjourmieuxmanger@gmail.com?subject=${encodeURIComponent(t('profile.contactSubject'))}`; }} chevron>
            <div>{t('profile.contact')}</div><div className="mut sm">{t('profile.contactSub')} · bonjourmieuxmanger@gmail.com</div>
          </Cell>
        </Group>
      </Section>
      <Section title={t('profile.localTitle')}>
        <Group>
          <Cell onPress={exp} chevron>{t('profile.export')}</Cell>
          <Cell onPress={() => setAskErase(true)}><span style={{ color: 'var(--bad)' }}>{t('profile.erase')}</span></Cell>
          <Cell onPress={() => { setCounting(countingOff()); location.reload(); }}>{countingOff() ? 'Autoriser le comptage anonyme des visites' : 'Ne pas me compter dans les visites'}</Cell>
          <Cell onPress={() => setNews((v) => !v)} chevron>{newsState() ? 'Nouveautés par e-mail : inscrit ✓' : 'Recevoir les nouveautés de Mieux'}</Cell>
          <Cell onPress={() => { location.href = '/confidentialite'; }} chevron>Confidentialité</Cell>
          <Cell onPress={() => { location.href = '/cgu'; }} chevron>Conditions d'utilisation</Cell>
          <Cell onPress={() => { location.href = '/mentions-legales'; }} chevron>Mentions légales</Cell>
          <Cell><span style={{ fontSize: 12, opacity: 0.7 }}>© {new Date().getFullYear()} Mieux. Tous droits réservés.</span></Cell>
        </Group>
      </Section>
      {news && <NewsModal onClose={() => setNews(false)} />}
      <Confirm open={askErase} onClose={() => setAskErase(false)} onConfirm={erase} title={t('profile.erase')} action={t('profile.erase')}>{t('profile.eraseConfirm')}</Confirm>
      <p className="about-credit">{t('brand.credit')}<br />Mieux {APP_VERSION}</p>
    </Screen>
  );
}
