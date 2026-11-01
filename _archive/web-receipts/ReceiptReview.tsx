import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useHistory } from '@shared/stores';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Group, Cell, Row, Pill, Toast } from '../ui';
import { routes, useNav } from '../nav';

/* eslint-disable @typescript-eslint/no-explicit-any */
const toCents = (s: string) => Math.round(parseFloat(s.replace(',', '.')) * 100) || 0;

export default function ReceiptReview() {
  const { go, back } = useNav();
  const parsed: any = (useLocation().state as any)?.parsed;
  const [retailer, setRetailer] = useState<string>(parsed?.retailer ?? '');
  const [date, setDate] = useState<string>(parsed?.purchase_date ?? new Date().toISOString().slice(0, 10));
  const [total, setTotal] = useState<number | null>(parsed?.total_cents ?? null);
  const [items, setItems] = useState<any[]>((parsed?.items ?? []).map((i: any) => ({ ...i, keep: true, link: false })));
  const addReceipt = useHistory((s) => s.addReceipt);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  if (!parsed) return <Screen><NavBar onBack={back} /><Card><Muted>{t('receipt.empty')}</Muted></Card><Button primary onPress={() => go(routes.receiptCapture)}>{t('home.scanReceipt')}</Button></Screen>;

  const kept = items.filter((i) => i.keep);
  const sum = kept.reduce((a, i) => a + i.line_total_cents, 0);
  const upd = (idx: number, patch: any) => setItems((L) => L.map((x, k) => (k === idx ? { ...x, ...patch } : x)));
  const save = async (allow = false) => {
    setSaving(true);
    try {
      await api.confirmReceipt({
        retailer: retailer || null, purchase_date: date || null, total_cents: total ?? sum, allow_duplicate: allow,
        items: kept.map((i) => ({ raw_description: i.raw, quantity: i.quantity, unit_price_cents: i.unit_price_cents, line_total_cents: i.line_total_cents, is_discount: i.is_discount,
          matched_product_id: i.link && i.match_candidate ? i.match_candidate.product_id : null, match_confidence: i.link && i.match_candidate ? i.match_candidate.score : null, extraction_confidence: i.extraction_confidence })),
      });
      addReceipt({ retailer: retailer || null, date: date || null, totalCents: total ?? sum, items: kept.map((i) => ({ raw: i.raw, lineTotalCents: i.line_total_cents, matched: i.link && i.match_candidate ? i.match_candidate.product_id : null })) });
      setToast(t('receipt.saved')); setTimeout(() => go(routes.purchases), 700);
    } catch (e: any) {
      if (e?.response?.status === 409 && confirm(t('receipt.dup'))) await save(true);
      else setToast(t('common.error'));
    } finally { setSaving(false); }
  };
  return (
    <Screen>
      <NavBar onBack={back} title={t('receipt.reviewTitle')} />
      <LargeTitle>{t('receipt.reviewTitle')}</LargeTitle>
      <Pill tone="w">{t('receipt.needsConfirm')}</Pill>
      <Group>
        <div className="field"><Muted>{t('receipt.shop')}</Muted><input value={retailer} onChange={(e) => setRetailer(e.target.value)} /></div>
        <div className="field"><Muted>{t('receipt.date')}</Muted><input value={date} onChange={(e) => setDate(e.target.value)} /></div>
      </Group>
      <Group>
        {items.map((i, k) => (
          <Cell key={k}>
            <Row>
              <input type="checkbox" checked={i.keep} onChange={(e) => upd(k, { keep: e.target.checked })} />
              <div className="grow" style={{ opacity: i.keep ? 1 : 0.4 }}>
                <input value={i.raw} onChange={(e) => upd(k, { raw: e.target.value })} style={{ padding: '6px 8px' }} />
                {i.extraction_confidence < 0.8 && <Muted>{t('receipt.lowConf')}</Muted>}
                <Pill tone={i.link ? undefined : i.match_candidate ? 'w' : 'g'}>{t('ms.' + (i.link ? 'confirmed' : i.match_candidate ? 'probable' : 'unidentified'))}</Pill>
                {i.match_candidate && <label className="mut sm"><input type="checkbox" checked={i.link} onChange={(e) => upd(k, { link: e.target.checked })} /> {t('receipt.linkTo', { n: i.match_candidate.name.slice(0, 28) })}</label>}
              </div>
              <input value={(i.line_total_cents / 100).toFixed(2)} onChange={(e) => { const c = toCents(e.target.value); upd(k, { line_total_cents: c, unit_price_cents: Math.round(c / (i.quantity || 1)) }); }} style={{ width: 84, padding: '6px 8px', textAlign: 'right' }} />
            </Row>
          </Cell>
        ))}
      </Group>
      <Card>
        <Row spread><span>{t('receipt.sum')}</span><b>{formatCents(sum)}</b></Row>
        <Row spread><span>{t('receipt.total')}</span><input style={{ width: 100, textAlign: 'right' }} value={total != null ? (total / 100).toFixed(2) : ''} onChange={(e) => setTotal(e.target.value ? toCents(e.target.value) : null)} /></Row>
        {total != null && (total === sum ? <Pill>{t('receipt.matchOk')}</Pill> : <p style={{ color: 'var(--bad)' }}>{t('receipt.mismatch', { d: formatCents(Math.abs(total - sum)) })}</p>)}
        {parsed.possible_duplicate && <Pill tone="b">{t('receipt.dup').split(' ?')[0]}</Pill>}
        {parsed.warnings?.map((w: string) => <p className="mut sm" key={w}>{w}</p>)}
      </Card>
      <p className="mut sm">{t('receipt.unmatchedHint')}</p>
      <Button primary disabled={saving || !kept.length} onPress={() => save()}>{saving ? t('receipt.saving') : t('receipt.confirm')}</Button>
      <Toast text={toast} />
    </Screen>
  );
}
