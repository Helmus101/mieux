import { Alert, Text } from 'react-native';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { Button, Card, Cell, Group, LargeTitle, Muted, NavBar, Screen, useTheme } from '../src/ui';
import { routes, useNav } from '../src/nav';

const when = (iso: string) => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }); } catch { return iso; } };

/** History: every scan kept on the device, newest first. Same screen as the web app's History. */
export default function History() {
  const c = useTheme();
  const { go, back } = useNav();
  const h = useHistory();
  const clear = () => Alert.alert(t('history.clearConfirm'), '', [{ text: t('common.cancel') }, { text: t('history.clear'), style: 'destructive', onPress: () => h.clear() }]);
  return (
    <Screen>
      <NavBar onBack={back} title={t('history.title')} />
      <LargeTitle sub={t('history.local')}>{t('history.title')}</LargeTitle>
      <Text style={{ color: c.mut, fontSize: 13, fontWeight: '600', marginTop: 18, marginBottom: 8 }}>{t('history.scans')} ({h.scans.length})</Text>
      {h.scans.length ? <Group>{h.scans.slice(0, 50).map((s, i, a) => (
        <Cell key={s.at} last={i === a.length - 1} chevron image={s.product.imageUrl ?? null} onPress={() => go(routes.product(s.id))}>
          <Text style={{ color: c.ink, fontWeight: '600' }}>{s.product.name}</Text>
          <Muted small>{s.product.brand} · {when(s.at)}</Muted>
        </Cell>
      ))}</Group> : <Card><Muted>{t('history.none')}</Muted></Card>}
      {h.scans.length ? <Button danger onPress={clear}>{t('history.clear')}</Button> : null}
      <Muted small>{t('history.local')}</Muted>
    </Screen>
  );
}
