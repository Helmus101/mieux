import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { clearAll } from '@shared/storage';
import { useProfile, useHistory, PRIORITY_KEYS } from '@shared/stores';
import { routes, useNav } from '../nav';
import { useState } from 'react';
import { Screen, NavBar, LargeTitle, Button, ChainLogo, Collapsible, Section, Chips, Chip, Group, Cell, Row, Segmented } from '../ui';
import { CHAIN_LIST } from '@shared/chains';
import { findCity, searchAddress, type Home } from '../place';
import { ADMIN_EMAIL, accountEnabled, signOut, useAccount } from '../account';
import AuthForm from '../AuthForm';

export default function Profile() {
  const p = useProfile();
  const { go } = useNav();
  const hist = useHistory();
  const [msg, setMsg] = useState(''), [, setTick] = useState(0);
  const [q, setQ] = useState(''), [sugg, setSugg] = useState<Home[]>([]);
  const email = useAccount((a) => a.email), scans = useAccount((a) => a.scans);
  const type = async (v: string) => { setQ(v); setSugg(await searchAddress(v)); };
  const locate = async () => { setMsg(''); const r = await findCity(); if (r === 'denied') setMsg(t('about.locDenied')); else if (!r) setMsg(t('about.locFail')); else p.setPlace(r); };
  const exp = async () => { const d = { server: await api.exportData().catch(() => null), device: hist.exportAll(), zone: p.zone }; const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 1)], { type: 'application/json' })); a.download = 'mieux-donnees.json'; a.click(); };
  const erase = async () => { if (!confirm(t('profile.eraseConfirm'))) return; await api.deleteAccount().catch(() => undefined); hist.clear(); clearAll(); p.reset(); location.href = '/'; };
  return (
    <Screen>
      <NavBar title={t('profile.title')} />
      <LargeTitle>{t('profile.title')}</LargeTitle>
      {accountEnabled && <Section title={t('account.title')}>
        {email ? <Group><Cell>{t('account.as', { x: email })}</Cell><Cell><Row spread><span>{t('account.scans')}</span><b>{scans ?? '…'}</b></Row></Cell>{email === ADMIN_EMAIL && <Cell onPress={() => go(routes.admin)} chevron>{t('admin.title')}</Cell>}<Cell onPress={() => { signOut(); }}>{t('account.out')}</Cell></Group> : <>
          <p className="mut sm">{t('account.hint')}</p>
          <AuthForm /></>}
      </Section>}
      <Section title={t('simple.loc')}>
        <input value={p.name ?? ''} onChange={(e) => p.setName(e.target.value)} placeholder={t('about.namePh')} autoComplete="given-name" />
        <input value={q} onChange={(e) => type(e.target.value)} placeholder={p.place ? (p.place.label ?? ([p.place.city, p.place.postcode].filter(Boolean).join(' · ') || t('about.addrPh'))) : t('about.addrPh')} autoComplete="street-address" style={{ marginTop: 12 }} />
        {sugg.map((a) => <Cell key={a.label} onPress={() => { p.setPlace(a); setQ(''); setSugg([]); }}>{a.label}</Cell>)}
        <Button onPress={locate}>{t('about.locBtn')}</Button>
        {msg && <p style={{ color: 'var(--warn)' }}>{msg}</p>}
        <p className="mut sm">{t('about.homeHint')}</p>
      </Section>
      <Section title={t('profile.language')}>
        <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k as 'fr' | 'en'); setTick((n) => n + 1); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      </Section>
      <Collapsible title={t('chains.title')}>
        <p className="mut sm" style={{ marginBottom: 8 }}>{t('chains.hint')}</p>
        <div className="chain-pick">{CHAIN_LIST.map((c) => { const on = (p.chains ?? []).includes(c.id); return <button key={c.id} className={'chain-chip' + (on ? ' on' : '')} onClick={() => p.toggleChain(c.id)}><ChainLogo id={c.id} name={c.name} size={22} />{c.name}</button>; })}</div>
        <p className="mut sm">{(p.chains ?? []).length ? t('chains.some', { n: (p.chains ?? []).length }) : t('chains.all')}{(p.chains ?? []).length > 0 && <> · <a onClick={() => p.clearChains()} style={{ cursor: 'pointer' }}>{t('chains.clear')}</a></>}</p>
      </Collapsible>
      <Section title={t('profile.priorities')}><Chips>{PRIORITY_KEYS.map((k) => <Chip key={k} on={p.priorities.includes(k)} onPress={() => p.togglePriority(k)}>{t('priorities.' + k)}</Chip>)}</Chips></Section>
      <Section title={t('profile.diet')}><Segmented value={p.diet} onChange={(k) => p.setDiet(k as 'omnivore' | 'vegetarian' | 'vegan')} options={(['omnivore', 'vegetarian', 'vegan'] as const).map((d) => ({ key: d, label: t('diets.' + d) }))} /></Section>
      <Section title={t('profile.restrictions')}><Chips>{['gluten', 'milk', 'peanuts', 'nuts'].map((a) => <Chip key={a} on={p.allergens.includes(a)} onPress={() => p.toggleAllergen(a)}>{t('diets.' + a)}</Chip>)}</Chips><p className="mut sm">{t('onboarding.allergyNote')}</p></Section>
      <Section title={t('profile.localTitle')}>
        <Group>
          <Cell onPress={() => go(routes.history)} chevron>{t('history.open')}</Cell>
          <Cell onPress={exp} chevron>{t('profile.export')}</Cell>
          <Cell onPress={erase}><span style={{ color: 'var(--bad)' }}>{t('profile.erase')}</span></Cell>
        </Group>
      </Section>
    </Screen>
  );
}
