import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { Card, Cell, Group, Hero, Muted, NavBar, Screen, Button } from '../ui';
import { routes, useNav } from '../nav';

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
      <h2>{t('history.scans')}</h2>
      {recent.length
        ? <Group>{recent.map((s) => <Cell key={s.id} image={s.product.imageUrl ?? ''} chevron onPress={() => go(routes.product(s.id))}><b>{s.product.name}</b><Muted>{s.product.brand}{s.product.score ? ` · ${s.product.score.total}/100` : ''}</Muted></Cell>)}</Group>
        : <><Card tint><h3>{t('home.startTitle')}</h3><Muted>{t('home.startText')}</Muted></Card>
          <Card><h3>{t('home.howTitle')}</h3>
            <ol className="how"><li>{t('home.how1')}</li><li>{t('home.how2')}</li><li>{t('home.how3')}</li></ol>
          </Card></>}
      <Card>
        <h3>📚 Blog</h3>
        <Muted>Conseils pour mieux manger et comprendre ce que vous consommez.</Muted>
        <div style={{ marginTop: 12 }}>
          <Button plain onPress={() => go(routes.blog)}>Voir tous les articles</Button>
        </div>
      </Card>
    </Screen>
  );
}
