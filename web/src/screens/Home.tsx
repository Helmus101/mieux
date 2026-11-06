import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { Brand, Cell, Group, Hero, Muted, Screen } from '../ui';
import { routes, useNav } from '../nav';
import DesktopQRBanner from '../DesktopQRBanner';
import { InstallCard } from '../InstallPrompt';
import { isPhone } from '../install';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Home() {
  const { go } = useNav();
  const { name, place } = useProfile();
  const scans = useHistory((s) => s.scans), savedCount = useHistory((s) => s.saved.length);
  const recent = scans.filter((s, i) => scans.findIndex((x) => x.id === s.id) === i).slice(0, 8);
  return (
    <Screen>
      <div className="apphead">
        <Brand />
        <button className="iconbtn" onClick={() => go(routes.list)} aria-label={t('list.title')}><svg viewBox="0 0 24 24" aria-hidden><path d="M6 4h12v17l-6-4.2L6 21z" /></svg>{savedCount > 0 && <em>{savedCount}</em>}</button>
      </div>
      <Hero title={name ? t('about.hello', { n: name }) : t('home.title')} sub={place ? place.city : t('home.sub')}>
        <button className="btn" onClick={() => go(routes.scan)}>{t('home.scanProduct')}</button>
      </Hero>
      <InstallCard />
      {!isPhone() && <DesktopQRBanner />}
      {recent.length > 0 && <>
        <h2>{t('history.scans')}</h2>
        <Group>{recent.map((s) => <Cell key={s.id} image={s.product.imageUrl || null} chevron onPress={() => go(routes.product(s.id))}><b>{s.product.name}</b><Muted>{s.product.brand}{s.product.score ? ` · ${s.product.score.total}/100` : ''}</Muted></Cell>)}</Group>
      </>}
      {recent.length === 0 && <div className="hsteps"><div><b>1</b>{t('home.s1')}</div><div><b>2</b>{t('home.s2')}</div><div><b>3</b>{t('home.s3')}</div></div>}
    </Screen>
  );
}
