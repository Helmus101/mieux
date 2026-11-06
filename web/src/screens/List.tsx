import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Group, Cell } from '../ui';
import { routes, useNav } from '../nav';

/** The saved list: every product the person bookmarked, from a product page or from the alternatives. */
export default function List() {
  const { go, back } = useNav();
  const saved = useHistory((s) => s.saved), remove = useHistory((s) => s.removeSaved), clearSaved = useHistory((s) => s.clearSaved);
  return (
    <Screen>
      <NavBar onBack={back} title={t('list.title')} />
      <LargeTitle sub={saved.length ? t('list.count', { n: saved.length }) : undefined}>{t('list.title')}</LargeTitle>
      {saved.length ? <>
        <Group>{saved.map((s) => (
          <Cell key={s.id} image={s.product.imageUrl || null} chevron onPress={() => go(routes.product(s.id))}>
            <div className="listrow"><div className="grow"><b>{s.product.name}</b><Muted>{[s.product.brand, s.product.score ? `${s.product.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted></div>
              <button className="iconbtn" aria-label={t('list.remove')} onClick={(e) => { e.stopPropagation(); remove(s.id); }}><svg viewBox="0 0 24 24" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg></button></div>
          </Cell>
        ))}</Group>
        <Button danger onPress={() => { if (confirm(t('list.clearConfirm'))) clearSaved(); }}>{t('list.clear')}</Button>
      </> : <Card><Muted>{t('list.empty')}</Muted></Card>}
    </Screen>
  );
}
