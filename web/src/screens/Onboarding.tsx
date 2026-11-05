import { useRef, useState } from 'react';
import { api } from '@shared/api/client';
import { t, setLocale } from '@shared/i18n';
import { useProfile, PRIORITY_KEYS } from '@shared/stores';
import { Button, Card, Cell, Muted, ChainLogo, Segmented } from '../ui';
import { accountEnabled, useAccount } from '../account';
import AuthForm from '../AuthForm';
import { InstallCard } from '../InstallPrompt';
import { chainsFor, COUNTRIES, type Country } from '@shared/chains';

const DIET: [string, string][] = [['omnivore', 'diet'], ['vegetarian', 'diet'], ['vegan', 'diet'], ['gluten', 'allergen'], ['milk', 'allergen'], ['peanuts', 'allergen'], ['nuts', 'allergen']];
const LIST = [...PRIORITY_KEYS, 'eco'];

export default function Onboarding({ gate = false }: { gate?: boolean }) {
  const p = useProfile();
  const [step, setStep] = useState(-1);
  const [address, setAddress] = useState('');
  const [sugg, setSugg] = useState<Awaited<ReturnType<typeof api.searchAddress>>>([]);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const type = (v: string) => {
    setAddress(v); clearTimeout(timer.current);
    if (v.trim().length < 3) { setSugg([]); return; }
    timer.current = setTimeout(() => { api.searchAddress(v).then(setSugg).catch(() => setSugg([])); }, 350);
  };
  const email = useAccount((a) => a.email);
  const okAbout = !!p.name?.trim(); // Location is now optional
  const chosen = p.chains ?? [];  // nothing chosen = every chain is shown
  if (step === -1) return (
    <div className="ob">
      <Segmented value={p.language ?? 'fr'} onChange={(k) => { p.setLanguage(k as 'fr' | 'en'); setLocale(k as 'fr' | 'en'); }} options={[{ key: 'fr', label: 'Français' }, { key: 'en', label: 'English' }]} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <div className="kicker">MIEUX</div><h1 style={{ fontSize: 38 }}>{t('welcome.title')}</h1><ul className="ob-points"><li>{t('welcome.p1')}</li><li>{t('welcome.p2')}</li><li>{t('welcome.p3')}</li></ul>
      </div>
      {accountEnabled && <Card>
        {email ? <b>{t('account.as', { x: email })}</b> : <>
          <p className="mut sm" style={{ margin: '0 0 10px' }}>{t('account.hint')}</p>
          <AuthForm /></>}
      </Card>}
      <InstallCard />
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
          <input value={address} onChange={(e) => type(e.target.value)} placeholder={t('about.addrPh')} autoComplete="street-address" />
          {sugg.map((a) => <Cell key={a.label} onPress={() => { p.setPlace(a); setAddress(''); setSugg([]); }}>{a.label}</Cell>)}
          {p.place && <p style={{ marginTop: 8, fontSize: 14, fontWeight: 500 }}>{p.place.label ?? p.place.city}</p>}
          {p.place && <Button small plain danger onPress={() => p.setPlace(null)}>{t('about.clear')}</Button>}
          {!p.place && <Button small plain onPress={() => setStep(1)}>{t('about.skip')}</Button>}
        </Card>
        <div style={{ flex: 1 }} />
        {!okAbout && <p className="mut sm">{t('welcome.need')}</p>}
        <Button primary disabled={!okAbout} onPress={() => setStep(1)}>{t('common.continue')}</Button>
      </>)}
      {step === 1 && (<>
        <h1 style={{ fontSize: 30 }}>{t('chains.title')}</h1><Muted>{t('chains.sub')}</Muted>
        <Segmented value={p.country ?? 'FR'} onChange={(k) => p.setCountry(k as Country)} options={COUNTRIES.map((c) => ({ key: c, label: t('country.' + c) }))} />
        {p.country === 'US' && <p className="mut sm">{t('country.usNote')}</p>}
        <div className="chain-pick" style={{ marginTop: 14 }}>{chainsFor(p.country).map((c) => { const on = chosen.includes(c.id); return <button key={c.id} className={'chain-chip' + (on ? ' on' : '')} onClick={() => p.toggleChain(c.id)}><ChainLogo id={c.id} name={c.name} size={22} />{c.name}</button>; })}</div>
        <div style={{ flex: 1 }} />
        <p className="mut sm">{chosen.length ? t('chains.some', { n: chosen.length }) : t('chains.all')}</p>
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
