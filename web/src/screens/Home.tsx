import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { Brand, Cell, Group, Muted, Screen } from '../ui';
import { routes, useNav } from '../nav';
import DesktopQRBanner from '../DesktopQRBanner';
import { InstallCard } from '../InstallPrompt';
import { isPhone } from '../install';

/* eslint-disable @typescript-eslint/no-explicit-any */
const tone = (n: number) => (n >= 70 ? 'g' : n >= 45 ? 'w' : 'b');

/** Home: one purpose (scan), then the last few products. Settings sit behind the icon, history behind "see all". */
export default function Home() {
  const { go } = useNav();
  const recent = useHistory((s) => s.scans).slice(0, 3);
  return (
    <Screen>
      <div className="apphead">
        <Brand />
        <button className="iconbtn" onClick={() => go(routes.profile)} aria-label={t('tabs.profile')}><svg viewBox="0 0 24 24" aria-hidden><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 00.3 1.9l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.9-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 01-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.9.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.9 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.9l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.9.3h0a1.7 1.7 0 001-1.5V3a2 2 0 014 0v.1a1.7 1.7 0 001 1.5h0a1.7 1.7 0 001.9-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.9v0a1.7 1.7 0 001.5 1H21a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z" /></svg></button>
      </div>
      <h1 className="greet">{t('home.title')}</h1>
      <p className="mut greet-sub">{t('home.tagline')}</p>
      <button className="scancard" onClick={() => go(routes.scan)}>
        <span className="scancard-icon"><svg viewBox="0 0 24 24" aria-hidden><path d="M4 8V5a1 1 0 011-1h3M16 4h3a1 1 0 011 1v3M20 16v3a1 1 0 01-1 1h-3M8 20H5a1 1 0 01-1-1v-3M7 12h10" /></svg></span>
        <b>{t('home.scanTitle')}</b>
        <small>{t('home.scanSub')}</small>
        <em>{t('home.scanGo')} →</em>
      </button>
      {recent.length > 0 && <>
        <div className="sechead"><h2>{t('home.recent')}</h2><button className="link" onClick={() => go(routes.history)}>{t('home.seeAll')} →</button></div>
        <Group>{recent.map((s) => (
          <Cell key={s.id} image={s.product.imageUrl || null} chevron onPress={() => go(routes.product(s.id))}>
            <div className="listrow"><div className="grow"><b>{s.product.name}</b><Muted>{s.product.brand}</Muted></div>
              {typeof s.product.score?.total === 'number' && <span className={'scorepill ' + tone(s.product.score.total)}>{s.product.score.total}</span>}</div>
          </Cell>
        ))}</Group>
      </>}
      <InstallCard />
      {!isPhone() && <DesktopQRBanner />}
    </Screen>
  );
}
