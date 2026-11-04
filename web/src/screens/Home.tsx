import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { Card, Cell, Group, Hero, Muted, NavBar, Screen } from '../ui';
import { routes, useNav } from '../nav';
import DesktopQRBanner from '../DesktopQRBanner';
import { InstallCard } from '../InstallPrompt';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Home() {
  const { go } = useNav();
  const { name, place } = useProfile();
  const scans = useHistory((s) => s.scans);
  const recent = scans.filter((s, i) => scans.findIndex((x) => x.id === s.id) === i).slice(0, 8);
  return (
    <Screen>
      <NavBar title={t('appName')} />
      <Hero title={name ? t('about.hello', { n: name }) : t('home.title')} sub={place ? place.city : t('home.sub')}>
        <button className="btn" onClick={() => go(routes.scan)}>{t('home.scanProduct')}</button>
      </Hero>
      <InstallCard />
      <DesktopQRBanner />
      <h2>{t('history.scans')}</h2>
      {recent.length
        ? <Group>{recent.map((s) => <Cell key={s.id} image={s.product.imageUrl ?? ''} chevron onPress={() => go(routes.product(s.id))}><b>{s.product.name}</b><Muted>{s.product.brand}{s.product.score ? ` · ${s.product.score.total}/100` : ''}</Muted></Cell>)}</Group>
        : <>
          <Card><h3>{t('home.howTitle')}</h3>
            <ol className="how"><li>{t('home.how1')}</li><li>{t('home.how2')}</li><li>{t('home.how3')}</li></ol>
          </Card></>}
    </Screen>
  );
}
