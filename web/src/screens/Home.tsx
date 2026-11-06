import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { Brand, Cell, Group, Muted, Screen } from '../ui';
import { routes, useNav } from '../nav';
import DesktopQRBanner from '../DesktopQRBanner';
import { InstallCard } from '../InstallPrompt';
import { isPhone } from '../install';

/* eslint-disable @typescript-eslint/no-explicit-any */
const tone = (n: number) => (n >= 70 ? 'g' : n >= 45 ? 'w' : 'b');

/** Home: what the shopper does (scan), then what they have done (real numbers from their own scans, never invented ones). */
export default function Home() {
  const { go } = useNav();
  const { name, place } = useProfile();
  const scans = useHistory((s) => s.scans), savedCount = useHistory((s) => s.saved.length);
  const scored = scans.map((s) => s.product?.score?.total).filter((x: any): x is number => typeof x === 'number');
  const avg = scored.length ? Math.round(scored.reduce((a: number, b: number) => a + b, 0) / scored.length) : null;
  const recent = scans.slice(0, 5);
  return (
    <Screen>
      <div className="apphead">
        <Brand />
        <button className="iconbtn" onClick={() => go(routes.list)} aria-label={t('tabs.list')}><svg viewBox="0 0 24 24" aria-hidden><path d="M6 4h12v17l-6-4.2L6 21z" /></svg>{savedCount > 0 && <em>{savedCount}</em>}</button>
      </div>
      <h1 className="greet">{name ? t('about.hello', { n: name }) : t('home.title')}</h1>
      <p className="mut greet-sub">{place ? place.city : t('home.tagline')}</p>
      <button className="scancard" onClick={() => go(routes.scan)}>
        <span className="scancard-icon"><svg viewBox="0 0 24 24" aria-hidden><path d="M4 8V5a1 1 0 011-1h3M16 4h3a1 1 0 011 1v3M20 16v3a1 1 0 01-1 1h-3M8 20H5a1 1 0 01-1-1v-3M7 12h10" /></svg></span>
        <b>{t('home.scanTitle')}</b>
        <small>{t('home.scanSub')}</small>
        <em>{t('home.scanGo')} →</em>
      </button>
      <InstallCard />
      {!isPhone() && <DesktopQRBanner />}
      {scans.length > 0 ? <>
        <div className="stats">
          <div><b>{scans.length}</b><span>{t('home.statAnalysed')}</span></div>
          <div><b>{savedCount}</b><span>{t('home.statSaved')}</span></div>
          <div><b>{avg ?? '—'}</b><span>{t('home.statAvg')}</span></div>
        </div>
        <div className="sechead"><h2>{t('home.recent')}</h2><button className="link" onClick={() => go(routes.history)}>{t('home.seeAll')} →</button></div>
        <Group>{recent.map((s) => (
          <Cell key={s.id} image={s.product.imageUrl || null} chevron onPress={() => go(routes.product(s.id))}>
            <div className="listrow"><div className="grow"><b>{s.product.name}</b><Muted>{s.product.brand}</Muted></div>
              {typeof s.product.score?.total === 'number' && <span className={'scorepill ' + tone(s.product.score.total)}>{s.product.score.total}</span>}</div>
          </Cell>
        ))}</Group>
      </> : <div className="hsteps"><div><b>1</b>{t('home.s1')}</div><div><b>2</b>{t('home.s2')}</div><div><b>3</b>{t('home.s3')}</div></div>}
    </Screen>
  );
}
