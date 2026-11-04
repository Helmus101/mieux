import { useState } from 'react';
import { t, setLocale } from '@shared/i18n';
import { useProfile, PRIORITY_KEYS } from '@shared/stores';
import { Button, Card, Muted, Pill, Cell, ChainLogo, Segmented } from '../ui';
import { accountEnabled, useAccount } from '../account';
import AuthForm from '../AuthForm';
import { CHAIN_LIST } from '@shared/chains';
import { findCity, searchAddress, type Home } from '../place';

const DIET: [string, string][] = [['omnivore', 'diet'], ['vegetarian', 'diet'], ['vegan', 'diet'], ['gluten', 'allergen'], ['milk', 'allergen'], ['peanuts', 'allergen'], ['nuts', 'allergen']];
const LIST = [...PRIORITY_KEYS, 'eco'];

export default function Onboarding({ gate = false }: { gate?: boolean }) {
  const p = useProfile();
  const [step, setStep] = useState(-1);
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState('');
  const [q, setQ] = useState(''), [sugg, setSugg] = useState<Home[]>([]);
  const email = useAccount((a) => a.email);
  const type = async (v: string) => { setQ(v); setSugg(await searchAddress(v)); };
  const okAbout = !!p.name?.trim(); // Location is now optional
  const all = CHAIN_LIST.map((c) => c.id);
  const kept = (p.chains ?? []).length ? p.chains! : all;           // nothing stored = every chain is kept
  const dislike = (id: string) => { const next = kept.includes(id) ? kept.filter((x) => x !== id) : [...kept, id]; if (next.length) p.setChains(next.length === all.length ? [] : next); };
  const locate = async () => {
    setBusy(true); setMsg('');
    const r = await findCity();
    if (r === 'denied') setMsg(t('about.locDenied')); else if (!r) setMsg(t('about.locFail')); else p.setPlace(r);
    setBusy(false);
  };
  if (step === -1) return (
    <div className="ob">
      <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k as 'fr' | 'en'); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div className="kicker">MIEUX</div><h1 style={{ fontSize: 38 }}>{t('welcome.title')}</h1><Muted>{t('welcome.sub')}</Muted>
      </div>
      {accountEnabled && <Card>
        {email ? <b>{t('account.as', { x: email })}</b> : <>
          <p className="mut sm" style={{ margin: '0 0 10px' }}>{t('account.hint')}</p>
          <AuthForm /></>}
      </Card>}
      {!gate && <Button primary disabled={accountEnabled && !email} onPress={() => setStep(0)}>{t('welcome.start')}</Button>}
    </div>
  );
  return (
    <div className="ob">
      <div className="dots"><i className={step === 0 ? 'on' : ''} /><i className={step === 1 ? 'on' : ''} /><i className={step === 2 ? 'on' : ''} /><i className={step === 3 ? 'on' : ''} /></div>
      {step === 0 && (<>
        <h1 style={{ fontSize: 30 }}>{t('about.title')}</h1><Muted>{t('about.sub')}</Muted>
        <p className="mut sm" style={{ marginBottom: 2 }}>{t('about.name')}</p>
        <input value={p.name ?? ''} onChange={(e) => p.setName(e.target.value)} placeholder={t('about.namePh')} autoComplete="given-name" />
        <Card>
          <b>{t('about.locTitle')}</b>
          <p className="mut sm" style={{ marginBottom: 8, fontSize: 13 }}>{t('about.locNote')}</p>
          {p.place ? <p><Pill tone={p.place.exact ? undefined : 'g'}>{p.place.label ?? ([p.place.city, p.place.postcode].filter(Boolean).join(' · '))}</Pill></p> : <p className="mut sm">{t('about.locHint')}</p>}
          <input value={q} onChange={(e) => type(e.target.value)} placeholder={t('about.addrPh')} autoComplete="street-address" />
          {sugg.map((a) => <Cell key={a.label} onPress={() => { p.setPlace(a); setQ(''); setSugg([]); }}>{a.label}</Cell>)}
          <Button disabled={busy} onPress={locate}>{busy ? t('about.locBusy') : p.place ? t('about.change') : t('about.locBtn')}</Button>
          {msg && <p style={{ color: 'var(--warn)' }}>{msg}</p>}
          {p.place && <Button small plain danger onPress={() => p.setPlace(null)}>{t('about.clear')}</Button>}
          {!p.place && <Button small plain onPress={() => setStep(1)}>{t('about.skip')}</Button>}
        </Card>
        <div style={{ flex: 1 }} />
        {!okAbout && <p className="mut sm">{t('welcome.need')}</p>}
        <Button primary disabled={!okAbout} onPress={() => setStep(1)}>{t('common.continue')}</Button>
      </>)}
      {step === 1 && (<>
        <h1 style={{ fontSize: 30 }}>{t('chains.title')}</h1><Muted>{t('chains.sub')}</Muted>
        <div className="chain-pick" style={{ marginTop: 14 }}>{CHAIN_LIST.map((c) => { const on = kept.includes(c.id); return <button key={c.id} className={'chain-chip' + (on ? ' on' : ' off')} onClick={() => dislike(c.id)}><ChainLogo id={c.id} name={c.name} size={22} />{c.name}</button>; })}</div>
        <div style={{ flex: 1 }} />
        <p className="mut sm">{kept.length === all.length ? t('chains.allKept') : t('chains.keptN', { n: kept.length })}</p>
        <Button primary onPress={() => setStep(2)}>{t('common.continue')}</Button>
        <Button plain onPress={() => setStep(0)}>{t('common.back')}</Button>
      </>)}
      {step === 2 && (<>
        <h1 style={{ fontSize: 30 }}>{t('onboarding.t1')}</h1>
        <Muted>{t('onboarding.s1')} · {t('onboarding.selected', { n: p.priorities.length })}</Muted>
        <div style={{ marginTop: 14 }}>
          {LIST.map((k) => (
            <button key={k} className={'opt' + (p.priorities.includes(k) ? ' on' : '')} style={k === 'eco' ? { opacity: 0.5 } : undefined} disabled={k === 'eco'} onClick={() => p.togglePriority(k)}>
              <b>{t('priorities.' + k)}</b><span className="tick" />
            </button>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        {!p.priorities.length && <p className="mut sm">{t('welcome.needPrio')}</p>}
        <Button primary disabled={!p.priorities.length} onPress={() => setStep(3)}>{t('common.continue')}</Button>
        <Button plain onPress={() => setStep(1)}>{t('common.back')}</Button>
      </>)}
      {step === 3 && (<>
        <h1 style={{ fontSize: 30 }}>{t('onboarding.t2')}</h1><Muted>{t('onboarding.s2')}</Muted>
        <div style={{ marginTop: 14 }}>
          {DIET.map(([k, kind]) => {
            const on = kind === 'diet' ? p.diet === k : p.allergens.includes(k);
            return (<button key={k} className={'opt' + (on ? ' on' : '')} onClick={() => (kind === 'diet' ? p.setDiet(k as never) : p.toggleAllergen(k))}><b>{t('diets.' + k)}</b><span className="tick" /></button>);
          })}
        </div>
        <Muted>{t('onboarding.allergyNote')}</Muted>
        <div style={{ flex: 1 }} />
        <Button primary onPress={() => p.finish()}>{t('onboarding.start')}</Button>
        <Button plain onPress={() => setStep(2)}>{t('common.back')}</Button>
      </>)}
    </div>
  );
}
