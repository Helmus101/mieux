import { useCallback, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { Button, Card, Cell, Group, LargeTitle, Muted, Pill, Row, Screen, Segmented, Skeleton, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Purchases() {
  const c = useTheme();
  const { go } = useNav();
  const [tab, setTab] = useState('receipts');
  const [rc, setRc] = useState<any[] | null>(null), [pu, setPu] = useState<any>(null);
  const load = useCallback(() => { api.getReceipts().then((x: any) => setRc(x.receipts)).catch(() => setRc([])); api.getPurchases().then(setPu).catch(() => undefined); }, []);
  useFocusEffect(load);
  const del = (id: number) => Alert.alert(t('purchases.deleteConfirm'), '', [{ text: t('common.cancel') }, { text: t('common.delete'), style: 'destructive', onPress: async () => { await api.deleteReceipt(id); load(); } }]);
  const rep = (pu?.purchases ?? []).filter((x: any) => x.times > 1);
  return (
    <Screen>
      <LargeTitle>{t('purchases.title')}</LargeTitle>
      <Button primary onPress={() => go(routes.receipt)}>{t('purchases.scan')}</Button>
      <Segmented value={tab} onChange={setTab} options={[{ key: 'receipts', label: t('purchases.receipts') }, { key: 'items', label: t('purchases.items') }, { key: 'prices', label: t('purchases.prices') }]} />
      {!rc && <Skeleton h={70} />}
      {tab === 'receipts' && rc && (rc.length ? <Group>{rc.map((r, i) => (<Cell key={r.id} last={i === rc.length - 1}><Row spread><View><Text style={{ color: c.ink, fontWeight: '600' }}>{r.retailer || '—'}</Text><Muted small>{r.purchase_date} · {t('purchases.lines', { n: r.lines })}</Muted></View>
        <View style={{ alignItems: 'flex-end' }}><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(r.total_cents)}</Text><Button small plain danger onPress={() => del(r.id)}>{t('common.delete')}</Button></View></Row></Cell>))}</Group> : <Card><Muted>{t('purchases.noReceipts')}</Muted></Card>)}
      {tab === 'items' && pu && <Group>{pu.purchases.map((x: any, i: number) => (
        <Cell key={x.key} last={i === pu.purchases.length - 1} onPress={x.product_id ? () => go(routes.product(x.product_id)) : undefined}><Text style={{ color: c.ink, fontWeight: '600' }}>{x.name}</Text>{!x.product_id && <Pill tone="g">{t('purchases.unmatched')}</Pill>}
          <Muted small>{t('purchases.boughtN', { n: x.times })} · {t('purchases.last', { p: formatCents(x.last_price_cents), s: x.history[0].retailer || '?', d: x.history[0].date || '?' })}</Muted></Cell>))}</Group>}
      {tab === 'prices' && pu && (rep.length ? rep.map((x: any) => <Card key={x.key}><Text style={{ color: c.ink, fontWeight: '600' }}>{x.name}</Text>{x.history.map((h: any, i: number) => <Row spread key={i}><Muted small>{h.date}</Muted><Text style={{ color: c.ink, fontWeight: '600' }}>{formatCents(h.unit_price_cents)}</Text></Row>)}</Card>) : <Card><Muted>{t('purchases.noPrices')}</Muted></Card>)}
      <Muted small>{pu?.note ?? t('purchases.note')}</Muted>
    </Screen>
  );
}
