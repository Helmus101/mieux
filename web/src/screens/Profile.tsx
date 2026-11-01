import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { clearAll } from '@shared/storage';
import { useProfile, useHistory, PRIORITY_KEYS } from '@shared/stores';
import { routes, useNav } from '../nav';
import { useState } from 'react';
import { Screen, NavBar, LargeTitle, Card, Button, ChainLogo, Collapsible, Muted, Section, Chips, Chip, Group, Cell, Row, Pill } from '../ui';
import { CHAIN_LIST } from '@shared/chains';
import { hapticsEnabled, setHapticsEnabled } from '../haptics';
import { findCity, searchAddress, type Home } from '../place';

export default function Profile() {
  const p = useProfile();
  const { go } = useNav();
  const hist = useHistory();
  const [msg, setMsg] = useState(''), [, setTick] = useState(0);
  const [q, setQ] = useState(''), [sugg, setSugg] = useState<Home[]>([]);
  const type = async (v: string) => { setQ(v); setSugg(await searchAddress(v)); };
  const locate = async () => { setMsg(''); const r = await findCity(); if (r === 'denied') setMsg(t('about.locDenied')); else if (!r) setMsg(t('about.locFail')); else p.setPlace(r); };
  const exp = async () => { const d = { server: await api.exportData().catch(() => null), device: hist.exportAll(), zone: p.zone }; const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 1)], { type: 'application/json' })); a.download = 'foodiq-donnees.json'; a.click(); };
  const erase = async () => { if (!confirm(t('profile.eraseConfirm'))) return; await api.deleteAccount().catch(() => undefined); hist.clear(); clearAll(); p.reset(); location.href = '/'; };
  return (
    <Screen>
      <NavBar title={t('profile.title')} />
      <LargeTitle>{t('profile.title')}</LargeTitle>
      <Section title={t('simple.loc')}>
        <input value={p.name ?? ''} onChange={(e) => p.setName(e.target.value)} placeholder={t('about.namePh')} autoComplete="given-name" />
        <Row spread><Pill tone={p.place?.lat != null ? undefined : 'g'}>{p.place ? (p.place.label ?? ([p.place.city, p.place.postcode].filter(Boolean).join(' · ') || t('about.locTitle'))) : t('about.locTitle')}</Pill><Button small onPress={locate}>{t('about.locBtn')}</Button></Row>
        <input value={q} onChange={(e) => type(e.target.value)} placeholder={t('about.addrPh')} autoComplete="street-address" />
        {sugg.map((a) => <Cell key={a.label} onPress={() => { p.setPlace(a); setQ(''); setSugg([]); }}>{a.label}</Cell>)}
        {msg && <p style={{ color: 'var(--warn)' }}>{msg}</p>}
        <p className="mut sm">{t('about.homeHint')}</p>
      </Section>
      <Section title={t('chains.title')}>
        <div className="chain-pick">{CHAIN_LIST.map((c) => { const on = (p.chains ?? []).includes(c.id); return <button key={c.id} className={'chain-chip' + (on ? ' on' : '')} onClick={() => p.toggleChain(c.id)}><ChainLogo id={c.id} name={c.name} size={22} />{c.name}</button>; })}</div>
        <p className="mut sm">{(p.chains ?? []).length ? t('chains.some', { n: (p.chains ?? []).length }) : t('chains.all')}{(p.chains ?? []).length > 0 && <> · <a onClick={() => p.clearChains()} style={{ cursor: 'pointer' }}>{t('chains.clear')}</a></>}</p>
      </Section>
      <Section title={t('profile.priorities')}><Chips>{PRIORITY_KEYS.map((k) => <Chip key={k} on={p.priorities.includes(k)} onPress={() => p.togglePriority(k)}>{t('priorities.' + k)}</Chip>)}</Chips></Section>
      <Section title={t('profile.diet')}><Chips>{(['omnivore', 'vegetarian', 'vegan'] as const).map((d) => <Chip key={d} on={p.diet === d} onPress={() => p.setDiet(d)}>{t('diets.' + d)}</Chip>)}</Chips></Section>
      <Section title={t('profile.restrictions')}><Chips>{['gluten', 'milk', 'peanuts', 'nuts'].map((a) => <Chip key={a} on={p.allergens.includes(a)} onPress={() => p.toggleAllergen(a)}>{t('diets.' + a)}</Chip>)}</Chips><p className="mut sm">{t('onboarding.allergyNote')}</p></Section>
      <Collapsible title={t('simple.advanced')}>
      <Section title={t('strict.title')}>
        <Group><Cell onPress={() => p.setStrictAdditives(!(p.strictAdditives !== false))}><Row spread><span><b>{p.strictAdditives !== false ? t('strict.on') : t('strict.off')}</b><Muted>{p.strictAdditives !== false ? t('strict.onSub') : t('strict.offSub')}</Muted></span><Pill tone={p.strictAdditives !== false ? undefined : 'g'}>{p.strictAdditives !== false ? 'On' : 'Off'}</Pill></Row></Cell></Group>
      </Section>
      <Section title={t('haptics.title')}>
        <Group><Cell onPress={() => { setHapticsEnabled(!hapticsEnabled()); setTick((n) => n + 1); }}><Row spread><span>{t('haptics.label')}</span><Pill tone={hapticsEnabled() ? undefined : 'g'}>{hapticsEnabled() ? 'On' : 'Off'}</Pill></Row></Cell></Group>
      </Section>
      <Section title={t('pricedb.title')}>
        <Group><Cell onPress={() => p.setEstimates(!p.estimates)}><Row spread><span><b>{t('pricedb.estToggle')}</b><Muted>{t('pricedb.estToggleSub')}</Muted></span><Pill tone={p.estimates ? 'w' : 'g'}>{p.estimates ? 'On' : 'Off'}</Pill></Row></Cell></Group>
      </Section>
      <Section title={t('profile.localTitle')}>
        <Card tint><p>{t('profile.localText')}</p><p className="mut">{t('profile.leaves')}</p></Card>
        <Group>
          <Cell onPress={() => go(routes.history)} chevron>{t('history.open')}</Cell>
          <Cell onPress={exp} chevron>{t('profile.export')}</Cell>
          <Cell onPress={erase}><span style={{ color: 'var(--bad)' }}>{t('profile.erase')}</span></Cell>
        </Group>
      </Section>
      <Section title={t('profile.how')}><Card><details><summary className="mut">{t('profile.how')}</summary><p className="mut">{t('profile.howText')}</p></details></Card></Section>
      <Button plain onPress={() => p.reset()}>{t('profile.reset')}</Button>
      </Collapsible>
    </Screen>
  );
}
