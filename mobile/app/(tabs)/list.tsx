import { Alert, Pressable, Text, View } from 'react-native';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { Button, Card, Cell, Group, LargeTitle, Muted, NavBar, Row, Screen, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';

/** Courses: the shopping destination. Saved products, plus the tools that work on them. Same screen as the web app's List. */
export default function List() {
  const c = useTheme();
  const { go } = useNav();
  const saved = useHistory((s) => s.saved), remove = useHistory((s) => s.removeSaved), clearSaved = useHistory((s) => s.clearSaved);
  const clear = () => Alert.alert(t('list.clearConfirm'), '', [{ text: t('common.cancel') }, { text: t('list.clear'), style: 'destructive', onPress: clearSaved }]);
  return (
    <Screen>
      <NavBar title={t('tabs.list')} />
      <LargeTitle sub={saved.length ? t('list.count', { n: saved.length }) : undefined}>{t('tabs.list')}</LargeTitle>
      {saved.length ? <>
        <Group>{saved.map((s, i) => (
          <Cell key={s.id} last={i === saved.length - 1} image={s.product.imageUrl ?? null} onPress={() => go(routes.product(s.id))}>
            <Row spread>
              <View style={{ flex: 1 }}>
                <Text style={{ color: c.ink, fontWeight: '600' }}>{s.product.name}</Text>
                <Muted small>{[s.product.brand, s.product.score ? `${s.product.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted>
              </View>
              <Pressable accessibilityLabel={t('list.remove')} hitSlop={10} onPress={() => { remove(s.id); }} style={{ padding: 6 }}>
                <Text style={{ color: c.mut, fontSize: 20 }}>✕</Text>
              </Pressable>
            </Row>
          </Cell>
        ))}</Group>
        <Button danger onPress={clear}>{t('list.clear')}</Button>
      </> : <Card><Muted>{t('list.empty')}</Muted></Card>}
      <Group>
        <Cell chevron onPress={() => go(routes.compare)}><Text style={{ color: c.ink, fontWeight: '600' }}>{t('list.compareTool')}</Text></Cell>
        <Cell chevron last onPress={() => go(routes.history)}><Text style={{ color: c.ink, fontWeight: '600' }}>{t('list.historyTool')}</Text></Cell>
      </Group>
    </Screen>
  );
}
