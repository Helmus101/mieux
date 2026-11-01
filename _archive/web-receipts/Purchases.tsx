import { useEffect, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Group, Cell, Segmented, Skeleton, Pill, Row } from '../ui';
import { routes, useNav } from '../nav';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function Purchases() {
  const { go } = useNav();
  const [tab, setTab] = useState('receipts');
  const [rc, setRc] = useState<any[] | null>(null);
  const [pu, setPu] = useState<any>(null);
  const load = () => { api.getReceipts().then((x: any) => setRc(x.receipts)).catch(() => setRc([])); api.getPurchases().then(setPu).catch(() => undefined); };
  useEffect(load, []);
  const del = async (id: number) => { if (confirm(t('purchases.deleteConfirm'))) { await api.deleteReceipt(id); load(); } };
  const exp = async () => { const d = await api.exportData(); const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 1)], { type: 'application/json' })); a.download = 'foodiq-donnees.json'; a.click(); };
  const rep = (pu?.purchases ?? []).filter((x: any) => x.times > 1);
  return (
    <Screen>
      <NavBar title={t('purchases.title')} />
      <LargeTitle>{t('purchases.title')}</LargeTitle>
      <Button primary onPress={() => go(routes.receiptCapture)}>{t('purchases.scan')}</Button>
      <Segmented value={tab} onChange={setTab} options={[{ key: 'receipts', label: t('purchases.receipts') }, { key: 'items', label: t('purchases.items') }, { key: 'prices', label: t('purchases.prices') }]} />
      {!rc && <Skeleton h={70} />}
      {tab === 'receipts' && rc && (rc.length ? <Group>{rc.map((r) => (
        <Cell key={r.id}><Row spread><span><b>{r.retailer || '—'}</b><Muted>{r.purchase_date} · {t('purchases.lines', { n: r.lines })}</Muted></span><span style={{ textAlign: 'right' }}><b>{formatCents(r.total_cents)}</b><br /><Button small plain danger onPress={() => del(r.id)}>{t('common.delete')}</Button></span></Row></Cell>
      ))}</Group> : <Card><Muted>{t('purchases.noReceipts')}</Muted></Card>)}
      {tab === 'items' && pu && <Group>{pu.purchases.map((x: any) => (
        <Cell key={x.key} onPress={x.product_id ? () => go(routes.product(x.product_id)) : undefined} chevron={!!x.product_id}>
          <b>{x.name}</b> {!x.product_id && <Pill tone="g">{t('purchases.unmatched')}</Pill>}
          <Muted>{t('purchases.boughtN', { n: x.times })} · {t('purchases.last', { p: formatCents(x.last_price_cents), s: x.history[0].retailer || '?', d: x.history[0].date || '?' })}</Muted>
        </Cell>))}</Group>}
      {tab === 'prices' && pu && (rep.length ? rep.map((x: any) => (
        <Card key={x.key}><b>{x.name}</b><table><tbody>{x.history.map((h: any, i: number) => <tr key={i}><td>{h.date}</td><td>{h.retailer}</td><td><b>{formatCents(h.unit_price_cents)}</b></td></tr>)}</tbody></table></Card>
      )) : <Card><Muted>{t('purchases.noPrices')}</Muted></Card>)}
      <p className="mut sm">{pu?.note ?? t('purchases.note')}</p>
      <Button plain onPress={exp}>{t('purchases.export')}</Button>
    </Screen>
  );
}
