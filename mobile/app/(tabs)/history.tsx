import { Alert, Image, Text, View } from 'react-native';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import * as hx from '../../src/haptics';
import { Button, Card, Cell, Group, LargeTitle, Muted, Row, Screen, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';

function fmt(iso: string) {
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

export default function History() {
  const { scans, clear } = useHistory();
  const { go } = useNav();
  const c = useTheme();
  const recent = scans.slice(0, 50);

  const confirmClear = () =>
    Alert.alert(t('history.clearConfirm'), '', [
      { text: t('common.cancel') },
      { text: t('history.clear'), style: 'destructive', onPress: () => { hx.heavy(); clear(); } },
    ]);

  return (
    <Screen>
      <LargeTitle>{t('history.title')}</LargeTitle>
      {recent.length === 0 ? (
        <Card tint>
          <Text style={{ color: c.ink, fontWeight: '600', marginBottom: 4 }}>{t('history.none')}</Text>
          <Muted small>{t('history.local')}</Muted>
        </Card>
      ) : (
        <Group>
          {recent.map((entry, i) => {
            const p = entry.product;
            const name: string = p?.name ?? p?.product_name ?? '—';
            const brand: string | null = p?.brand ?? p?.brands ?? null;
            const img: string | null = p?.image_url ?? p?.image_front_url ?? null;
            return (
              <Cell
                key={entry.at}
                last={i === recent.length - 1}
                onPress={() => { hx.select(); go(routes.product(entry.id)); }}
              >
                <Row>
                  {img ? (
                    <Image
                      source={{ uri: img }}
                      style={{ width: 44, height: 44, borderRadius: 8, backgroundColor: c.line }}
                      resizeMode="contain"
                    />
                  ) : (
                    <View style={{ width: 44, height: 44, borderRadius: 8, backgroundColor: c.line }} />
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: c.ink, fontWeight: '600', fontSize: 15 }} numberOfLines={1}>{name}</Text>
                    {brand ? <Muted small>{brand}</Muted> : null}
                    <Muted small>{fmt(entry.at)}</Muted>
                  </View>
                </Row>
              </Cell>
            );
          })}
        </Group>
      )}
      {recent.length > 0 && (
        <Button plain danger onPress={confirmClear}>{t('history.clear')}</Button>
      )}
    </Screen>
  );
}
