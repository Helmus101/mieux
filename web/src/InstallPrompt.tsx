import { useEffect, useState } from 'react';
import { t } from '@shared/i18n';
import { Button, Sheet, haptic } from './ui';
import { OPEN_EVENT, hideHint, hintHidden, isInstalled, platform, shouldHint } from './install';

interface BIP extends Event { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> }
const ShareIcon = () => <svg viewBox="0 0 24 24" width="20" height="20" style={{ verticalAlign: 'middle', stroke: 'var(--blue)', fill: 'none', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' }}><path d="M12 15V4M8 8l4-4 4 4M6 12v7a1 1 0 001 1h10a1 1 0 001-1v-7" /></svg>;

/** A small banner on phones that are not using the installed app, plus a sheet with the steps for iPhone and Android. Also opened from the profile. */
export default function InstallPrompt({ hidden, bare }: { hidden?: boolean; bare?: boolean }) {
  const [banner, setBanner] = useState(() => shouldHint() && !hintHidden());
  const [open, setOpen] = useState(false), [tab, setTab] = useState(platform() === 'android' ? 'android' : 'ios');
  const [native, setNative] = useState<BIP | null>(null);
  useEffect(() => {
    const onBip = (e: Event) => { e.preventDefault(); setNative(e as BIP); };
    const onOpen = () => { setTab(platform() === 'android' ? 'android' : 'ios'); setOpen(true); };
    const onDone = () => { setBanner(false); setOpen(false); };
    window.addEventListener('beforeinstallprompt', onBip); window.addEventListener(OPEN_EVENT, onOpen); window.addEventListener('appinstalled', onDone);
    return () => { window.removeEventListener('beforeinstallprompt', onBip); window.removeEventListener(OPEN_EVENT, onOpen); window.removeEventListener('appinstalled', onDone); };
  }, []);
  const later = () => { haptic('tap'); hideHint(); setBanner(false); setOpen(false); };
  const install = async () => {
    if (!native) { setOpen(true); return; }
    haptic('tap'); await native.prompt();
    const r = await native.userChoice.catch(() => null);
    if (r?.outcome === 'accepted') { setBanner(false); setOpen(false); }
    setNative(null);
  };
  if (isInstalled()) return null;
  return (<>
    {banner && !hidden && (
      <div className={bare ? 'install-banner bare' : 'install-banner'} role="region" aria-label={t('pwa.title')}>
        <img src="/icon-180.png" alt="" width={44} height={44} />
        <div className="grow"><b>{t('pwa.title')}</b><div className="mut sm">{t('pwa.sub')}</div></div>
        <Button small primary onPress={() => (native && platform() === 'android' ? install() : (haptic('tap'), setOpen(true)))}>{t('pwa.how')}</Button>
        <button className="install-x" onClick={later} aria-label={t('pwa.later')}>×</button>
      </div>)}
    <Sheet open={open} onClose={() => setOpen(false)} title={t('pwa.sheetTitle')}>
      <p className="mut">{t('pwa.why')}</p>
      <div className="seg" role="tablist">
        {(['ios', 'android'] as const).map((k) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => { haptic('select'); setTab(k); }}>{t('pwa.' + k)}</button>)}
      </div>
      {tab === 'ios' ? (
        <ol className="steps">
          <li>{t('pwa.ios1')}</li>
          <li>{t('pwa.ios2a')} <ShareIcon /> {t('pwa.ios2b')}</li>
          <li>{t('pwa.ios3')}</li>
          <li>{t('pwa.ios4')}</li>
        </ol>
      ) : (
        <ol className="steps">
          <li>{t('pwa.and1')}</li>
          <li>{t('pwa.and2')}</li>
          <li>{t('pwa.and3')}</li>
          <li>{t('pwa.and4')}</li>
        </ol>
      )}
      {tab === 'android' && native && <Button primary onPress={install}>{t('pwa.installNow')}</Button>}
      <p className="mut sm">{tab === 'ios' ? t('pwa.iosNote') : t('pwa.andNote')}</p>
      <Button plain onPress={later}>{t('pwa.later')}</Button>
    </Sheet>
  </>);
}
