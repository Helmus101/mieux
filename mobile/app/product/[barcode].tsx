import { useEffect, useState } from 'react';
import { Image, Linking, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { api } from '@shared/api/client';
import { additiveInfo } from '@shared/additives';
import { t } from '@shared/i18n';
import { formatCents } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { priceHeadline, verdictOf } from '@shared/verdict';
import { Bar, Body, Button, Card, Cell, Chip, Chips, Collapsible, Group, Muted, NovaBadge, NutriScore, Pill, Row, Screen, Sheet, Skeleton, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import * as hx from '../../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const f1 = (v: number | null | undefined, u = 'g') => (v == null ? t('common.missing') : `${Math.round(v * 10) / 10} ${u}`);
const label = (x: any) => (x.priority.startsWith('allergen:') ? t('diets.' + x.priority.split(':')[1]) : t('priorities.' + x.priority));

export default function Product() {
  const c = useTheme();
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const { go, back } = useNav();
  const estimates = useProfile((s) => s.estimates), addCompare = useProfile((s) => s.addCompare);
  const hist = useHistory();
  const [d, setD] = useState<any>(null), [err, setErr] = useState(''), [offline, setOffline] = useState(false);
  const [sheet, setSheet] = useState<string | null>(null), [tick] = useState(0);
  useEffect(() => {
    if (!barcode) return;
    setErr(''); setOffline(false);
    api.getProduct(barcode, estimates).then((x: any) => { setD(x); hist.addScan(x.product); api.addScan(barcode).catch(() => undefined); if (x.fit?.some((f: any) => f.status === 'conflict')) hx.warning(); else hx.success(); })
      .catch((e: any) => { const snap = useHistory.getState().productById(barcode); if (snap && e?.response?.status !== 404) { setD({ product: snap, fit: [], price_context: null }); setOffline(true); } else setErr(e?.response?.status === 404 ? t('product.notFoundText') : e.message); });
  }, [barcode, estimates, tick]);
  if (err) return <Screen><Text style={{ color: c.ink, fontSize: 24, fontWeight: '700' }}>{t('product.notFound')}</Text><Muted>{err}</Muted><Button primary onPress={back}>{t('common.back')}</Button></Screen>;
  if (!d) return <Screen><Skeleton h={90} /><Skeleton h={120} /><Skeleton h={60} /></Screen>;

  const p = d.product, n = p.nutriments, pc = d.price_context;
  const verdict = verdictOf(d.fit), head = priceHeadline(pc);
  const info = sheet ? additiveInfo(sheet) : null;

  return (
    <Screen>
      <Row spread><Button small plain onPress={back}>‹ {t('common.back')}</Button></Row>
      {offline && <Pill tone="w">{t('history.offline')}</Pill>}
      <Row>{p.imageUrl ? <Image source={{ uri: p.imageUrl }} style={{ width: 88, height: 88, borderRadius: 16, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
        <View style={{ flex: 1 }}><Muted>{p.brand}</Muted><Text style={{ color: c.ink, fontSize: 22, fontWeight: '700' }}>{p.name}</Text><Muted small>{p.quantityText}</Muted></View></Row>

      <Card>
        {verdict && <Pill tone={verdict.tone}>{verdict.text}</Pill>}
        <View style={{ marginTop: 10 }}>
          {head.kind !== 'none' ? <><Text style={{ color: c.ink, fontSize: 30, fontWeight: '700' }}>{head.kind === 'estimate' ? '~ ' : ''}{t('simple.perKg', { p: formatCents(head.perKgCents!) })}</Text>{head.kind === 'estimate' ? <Pill tone="w">{t('est.pill')}</Pill> : null}</>
            : <Text style={{ color: c.mut, fontSize: 18 }}>{t('simple.noPrice')}</Text>}
        </View>
        <Row style={{ marginTop: 10 }}><NutriScore grade={p.nutriScore} /><NovaBadge group={p.novaGroup} estimated={p.novaEstimated} /></Row>
      </Card>
      <Button primary onPress={() => go(routes.alternatives(p.id))}>{t('simple.findBetter')}</Button>

      <Collapsible title={t('simple.priceSec')}>
        {pc?.history?.length ? pc.history.slice(0, 5).map((h: any) => (
          <Row spread key={h.id}><View style={{ flex: 1 }}><Body bold>{h.currency && h.currency !== 'EUR' && h.price_native != null ? `${h.price_native.toFixed(2).replace('.', ',')} ${h.currency} ≈ ${h.pack_cents != null ? formatCents(h.pack_cents) : '—'}` : h.pack_cents != null ? formatCents(h.pack_cents) : '—'}</Body><Muted small>{h.date}</Muted></View><Pill tone={h.source === 'estimate' ? 'w' : undefined}>{t('pricedb.' + h.source)}</Pill></Row>))
          : <Muted>{t('pricedb.noneReal')}</Muted>}
        <Muted small>{t('pricedb.footer')}</Muted>
      </Collapsible>
      <Collapsible title={t('simple.nutSec')}>
        {([['energy', f1(n.energyKcal100g, 'kcal')], ['fat', f1(n.fat100g)], ['sat', f1(n.saturatedFat100g)], ['carbs', f1(n.carbohydrates100g)], ['sugars', f1(n.sugars100g)], ['protein', f1(n.protein100g)], ['fibre', f1(n.fiber100g)], ['salt', f1(n.salt100g)]] as const).map(([k, v]) => <Row spread key={k}><Body>{t('product.' + k)}</Body><Body bold>{v}</Body></Row>)}
        {d.fit.length > 0 && d.fit.map((x: any) => <Row spread key={x.priority}><Muted small>{label(x)}</Muted><Pill tone={x.status === 'match' ? undefined : x.status === 'partial' || x.status === 'unknown' ? 'w' : 'b'}>{t('product.st.' + x.status)}</Pill></Row>)}
      </Collapsible>
      {p.micronutrients?.length > 0 && <Collapsible title={t('simple.microSec')}>{p.micronutrients.map((m: any) => (<View key={m.key} style={{ marginVertical: 6 }}><Row spread><Body>{t('micro.' + m.key)}</Body><Muted small>{m.amount} {m.unit} · {m.nrv_pct}%</Muted></Row><Bar value={Math.min(1, m.nrv_pct / 100)} /></View>))}<Muted small>{t('micro.note')}</Muted></Collapsible>}
      <Collapsible title={`${t('simple.addSec')} (${p.additives.length})`}>{p.additives.length ? <Chips>{p.additives.map((a: string) => <Chip key={a} onPress={() => setSheet(a)}>{a.toUpperCase()}{additiveInfo(a) ? ' · ' + additiveInfo(a)!.name : ''}</Chip>)}</Chips> : <Muted>{t('product.none')}</Muted>}</Collapsible>
      <Collapsible title={t('simple.ingSec')}>
        <Muted>{p.ingredientsText || t('product.noIng')}</Muted>
        <View style={{ marginTop: 8 }}>{p.allergens.length ? <Chips>{p.allergens.map((a: string) => <Pill key={a} tone="w">{a}</Pill>)}</Chips> : <Muted small>{p.ingredientsText ? t('product.allergenNone') : t('product.allergenMissing')}</Muted>}</View>
      </Collapsible>
      <Button plain onPress={() => { addCompare(p.id); go(routes.compare); }}>{t('product.compare')}</Button>

      <Sheet open={!!sheet} onClose={() => setSheet(null)} title={sheet ? sheet.toUpperCase() + (info ? ' · ' + info.name : '') : ''}>
        {info ? <><Body bold>{t('add.why')}</Body><Muted>{info.why}</Muted><Body bold>{t('add.evidence')}</Body><Muted>{info.evidence}</Muted><Body bold>{t('add.regulation')}</Body><Muted>{info.regulation}</Muted><Body bold>{t('add.advice')}</Body><Muted>{info.advice}</Muted><Button small plain onPress={() => Linking.openURL(info.source)}>{t('add.source')} : EFSA / UE</Button></> : <Muted>{t('add.unknown')}</Muted>}
        <Button onPress={() => setSheet(null)}>{t('common.done')}</Button>
      </Sheet>
    </Screen>
  );
}
