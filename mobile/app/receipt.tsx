import { useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useHistory } from '@shared/stores';
import { Body, Button, Card, Cell, Field, Group, LargeTitle, Muted, Pill, Row, Screen, Toast, useTheme } from '../src/ui';
import { routes, useNav } from '../src/nav';
import { recognizeReceipt } from '../src/ocr';
import * as hx from '../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const toCents = (s: string) => Math.round(parseFloat(s.replace(',', '.')) * 100) || 0;

export default function Receipt() {
  const c = useTheme();
  const { go, back } = useNav();
  const addReceipt = useHistory((s) => s.addReceipt);
  const [txt, setTxt] = useState('');
  const [msg, setMsg] = useState('');
  const [pv, setPv] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [retailer, setRetailer] = useState(''), [date, setDate] = useState(''), [toast, setToast] = useState<string | null>(null);

  const parse = async (text: string) => {
    const lines = text.split('\n').map((l, i) => ({ text: l.trim(), confidence: 0.9, position: i })).filter((l) => l.text);
    const r = await api.previewReceipt(lines);
    setPv(r); setRetailer(r.retailer ?? ''); setDate(r.purchase_date ?? new Date().toISOString().slice(0, 10)); setItems(r.items.map((i: any) => ({ ...i, keep: true, link: false })));
  };
  const fromPhoto = async () => { setMsg(''); const r = await recognizeReceipt(); if (r.text) await parse(r.text); else setMsg(r.reason ?? t('receipt.fail')); };
  const kept = items.filter((i) => i.keep), sum = kept.reduce((a, i) => a + i.line_total_cents, 0), total = pv?.total_cents ?? null;
  const save = async (allow = false) => {
    try {
      await api.confirmReceipt({ retailer: retailer || null, purchase_date: date || null, total_cents: total ?? sum, allow_duplicate: allow,
        items: kept.map((i) => ({ raw_description: i.raw, quantity: i.quantity, unit_price_cents: i.unit_price_cents, line_total_cents: i.line_total_cents, is_discount: i.is_discount,
          matched_product_id: i.link && i.match_candidate ? i.match_candidate.product_id : null, match_confidence: i.link && i.match_candidate ? i.match_candidate.score : null, extraction_confidence: i.extraction_confidence })) });
      addReceipt({ retailer: retailer || null, date: date || null, totalCents: total ?? sum, items: kept.map((i) => ({ raw: i.raw, lineTotalCents: i.line_total_cents, matched: i.link && i.match_candidate ? i.match_candidate.product_id : null })) });
      hx.success(); setToast(t('receipt.saved')); setTimeout(() => go(routes.purchases), 700);
    } catch (e: any) {
      if (e?.response?.status === 409) { hx.warning(); Alert.alert(t('receipt.dup'), '', [{ text: t('common.cancel') }, { text: t('pricedb.save'), onPress: () => save(true) }]); }
      else { hx.error(); setToast(t('common.error')); }
    }
  };
  if (!pv) return (
    <Screen>
      <Button small plain onPress={back}>‹ {t('common.back')}</Button>
      <LargeTitle sub={t('receipt.captureText')}>{t('receipt.captureTitle')}</LargeTitle>
      <Button primary onPress={fromPhoto}>{t('receipt.take')}</Button>{msg ? <Muted>{msg}</Muted> : null}
      <Card><Body bold>{t('receipt.or')}</Body><Field value={txt} onChangeText={setTxt} multiline placeholder={'MONOPRIX\n28/10/2026\nYAOURT GREC 1,59\nTOTAL 1,59'} /><Button onPress={() => txt.trim() && parse(txt)}>{t('receipt.parse')}</Button></Card>
    </Screen>);
  return (
    <Screen>
      <LargeTitle>{t('receipt.reviewTitle')}</LargeTitle><Pill tone="w">{t('receipt.needsConfirm')}</Pill>
      <Group><View style={{ padding: 10 }}><Muted small>{t('receipt.shop')}</Muted><Field value={retailer} onChangeText={setRetailer} /><Muted small>{t('receipt.date')}</Muted><Field value={date} onChangeText={setDate} /></View></Group>
      <Group>{items.map((i, k) => (
        <Cell key={k} last={k === items.length - 1}><Row spread>
          <View style={{ flex: 1, opacity: i.keep ? 1 : 0.4 }}>
            <Text style={{ color: c.ink, fontWeight: '600' }}>{i.raw}</Text>
            <Pill tone={i.link ? undefined : i.match_candidate ? 'w' : 'g'}>{t('ms.' + (i.link ? 'confirmed' : i.match_candidate ? 'probable' : 'unidentified'))}</Pill>
            {i.match_candidate ? <Button small plain onPress={() => setItems((L) => L.map((x, j) => (j === k ? { ...x, link: !x.link } : x)))}>{t('receipt.linkTo', { n: String(i.match_candidate.name).slice(0, 26) })}{i.link ? ' ✓' : ''}</Button> : null}</View>
          <View style={{ alignItems: 'flex-end' }}><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(i.line_total_cents)}</Text>
            <Button small plain danger={i.keep} onPress={() => setItems((L) => L.map((x, j) => (j === k ? { ...x, keep: !x.keep } : x)))}>{i.keep ? t('common.delete') : '+'}</Button></View></Row></Cell>))}</Group>
      <Card><Row spread><Muted>{t('receipt.sum')}</Muted><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(sum)}</Text></Row>
        {total != null && <Row spread><Muted>{t('receipt.total')}</Muted><Text style={{ color: c.ink, fontWeight: '700' }}>{formatCents(total)}</Text></Row>}
        {total != null && (total === sum ? <Pill>{t('receipt.matchOk')}</Pill> : <Text style={{ color: c.bad }}>{t('receipt.mismatch', { d: formatCents(Math.abs(total - sum)) })}</Text>)}</Card>
      <Muted small>{t('receipt.unmatchedHint')}</Muted>
      <Button primary disabled={!kept.length} onPress={() => save()}>{t('receipt.confirm')}</Button>
      <Button plain onPress={() => setPv(null)}>{t('common.cancel')}</Button>
      <Toast text={toast} />
    </Screen>
  );
}
