import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { useState } from 'react';
import { Screen, NavBar, LargeTitle, Button, Muted, Group, Cell, Confirm } from '../ui';
import { routes, useNav } from '../nav';

/** Courses: the shopping destination. Saved products (from a product page or from the alternatives), plus the tools that work on them. */
export default function List() {
  const { go } = useNav();
  const saved = useHistory((s) => s.saved), remove = useHistory((s) => s.removeSaved), clearSaved = useHistory((s) => s.clearSaved);
  const [ask, setAsk] = useState(false);
  return (
    <Screen>
      <NavBar />
      <LargeTitle sub={saved.length ? t('list.count', { n: saved.length }) : undefined}>{t('tabs.list')}</LargeTitle>
      {saved.length ? <>
        <Group>{saved.map((s) => (
          <Cell key={s.id} image={s.product.imageUrl || null} chevron onPress={() => go(routes.product(s.id))}>
            <div className="listrow"><div className="grow"><b>{s.product.name}</b><Muted>{[s.product.brand, s.product.score ? `${s.product.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted></div>
              <button className="iconbtn" aria-label={t('list.remove')} onClick={(e) => { e.stopPropagation(); remove(s.id); }}><svg viewBox="0 0 24 24" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg></button></div>
          </Cell>
        ))}</Group>
        <Button danger onPress={() => setAsk(true)}>{t('list.clear')}</Button>
        <Confirm open={ask} onClose={() => setAsk(false)} onConfirm={clearSaved} title={t('list.clear')} action={t('common.delete')}>{t('list.clearConfirm')}</Confirm>
      </> : <div className="empty"><p>{t('list.empty')}</p><Button primary onPress={() => go(routes.scan)}>{t('tabs.scan')}</Button></div>}
      <Group>
        <Cell chevron onPress={() => go(routes.history)}><b>{t('list.historyTool')}</b></Cell>
      </Group>
    </Screen>
  );
}
