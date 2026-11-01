import { useEffect, useState } from 'react';
import { Image, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory, useProfile, PRIORITY_KEYS } from '@shared/stores';
import { Button, Card, Chip, Chips, Collapsible, Muted, NovaBadge, NutriScore, Pill, Row, Screen, Segmented, Skeleton, Toast, useTheme } from '../../src/ui';
import { routes, useNav } from '../../src/nav';
import * as hx from '../../src/haptics';

/* eslint-disable @typescript-eslint/no-explicit-any */
const eur = (v: number | null | undefined) => (v == null ? '—' : v.toFixed(2).replace('.', ',') + ' €');
const saveBy = (r: any, per100: number | null | undefined) => { const o = r?.original_price; if (!o || o.pack_cents == null || per100 == null || !o.per100_cents) return 0; return Math.max(0, Math.round((o.per100_cents - per100) * o.pack_cents / o.per100_cents)); };

export default function Alternatives() {
  const c = useTheme();
  const { barcode } = useLocalSearchParams<{ barcode: string }>();
  const { go, back } = useNav();
  const saved = useProfile((s) => s.priorities), estimates = useProfile((s) => s.estimates), addCompare = useProfile((s) => s.addCompare);
  const addSearch = useHistory((s) => s.addSearch);
  const [prios, setPrios] = useState<string[]>(saved.length ? saved : ['value']);
  const [mode, setMode] = useState('similar'), [pc, setPc] = useState('any'), [rk, setRk] = useState('match'), [touched, setTouched] = useState(false);
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState('');
  const [expl, setExpl] = useState<Record<string, any>>({}), [chosen, setChosen] = useState<string[]>([]), [note, setNote] = useState<string | null>(null);
  const toggle = (k: string) => setPrios((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p, k].slice(-2)));
  useEffect(() => {
    if (!barcode || !prios.length) return;
    setBusy(true); setErr('');
    api.getAlternatives(barcode, { priorities: prios, category_mode: mode, limit: 5, price_constraint: pc, approximate: estimates })
      .then((x: any) => { setR(x); if (!touched && x.budget?.recommended_ranking) setRk(x.budget.recommended_ranking); addSearch({ originalId: barcode, originalName: x.original?.name ?? barcode, priorities: prios, mode, results: x.alternatives.map((a: any) => ({ id: a.product_id, name: a.product.name, brand: a.product.brand, priceCents: a.price_per_100_cents != null ? Math.round(a.price_per_100_cents) : null })) }); })
      .catch((e: Error) => setErr(e.message)).finally(() => setBusy(false));
  }, [barcode, prios, mode, pc, estimates]);
  const explain = async (id: string) => { setExpl((e) => ({ ...e, [id]: { loading: true } })); try { const x = await api.explain(barcode!, id); setExpl((e) => ({ ...e, [id]: x })); } catch { setExpl((e) => ({ ...e, [id]: null })); } };
  const entries = rk === 'match' ? (r?.alternatives ?? []).map((a: any) => ({ product: a.product, why: a.improvements.join(' ; '), tradeoffs: a.tradeoffs, price100: a.price_per_100_cents, estimated: a.estimated, sizes: a.other_sizes })) : (r?.rankings?.[rk] ?? []).map((e: any) => ({ product: e.product, why: e.why, tradeoffs: e.tradeoffs, price100: e.price_per_100_cents, estimated: e.estimated, dominated: e.dominated }));
  return (
    <Screen>
      <Button small plain onPress={back}>‹ {t('common.back')}</Button>
      <Text style={{ color: c.ink, fontSize: 30, fontWeight: '800' }}>{t('alt.title')}</Text>
      {r?.original && <Muted>{r.original.name}</Muted>}
      <Segmented value={rk} onChange={(k) => { setTouched(true); setRk(k); }} options={[{ key: 'budget', label: t('rank.budget') }, { key: 'value', label: t('rank.value') }, { key: 'match', label: t('rank.match') }]} />
      <Muted small>{t('rank.' + rk + 'Sub')}</Muted>
      {r?.budget && <Card tint><Text style={{ color: c.ink, fontWeight: '600' }}>{t('bud.advice.' + r.budget.recommended_ranking)}</Text></Card>}
      <Collapsible title={t('simple.filtersT')}>
        <Chips>{PRIORITY_KEYS.map((k) => <Chip key={k} on={prios.includes(k)} onPress={() => toggle(k)}>{t('priorities.' + k)}</Chip>)}</Chips>
        <Segmented value={pc} onChange={setPc} options={[{ key: 'any', label: t('cstr.any') }, { key: 'cheaper', label: t('cstr.cheaper') }, { key: 'same_or_cheaper', label: t('cstr.same') }]} />
        <Segmented value={mode} onChange={setMode} options={[{ key: 'similar', label: t('alt.similar') }, { key: 'any', label: t('alt.any') }]} />
      </Collapsible>
      {busy && <><Skeleton h={150} /><Skeleton h={150} /></>}
      {err ? <Card><Muted>{err}</Muted></Card> : null}
      {r && !busy && !entries.length && <Card><Text style={{ color: c.ink, fontWeight: '600' }}>{rk === 'match' ? r.no_recommendation_reason : t('rank.empty')}</Text><Muted small>{t('simple.tryFilters')}</Muted></Card>}
      {r && !busy && entries.map((e: any, i: number) => {
        const sv = saveBy(r, e.price100);
        return (
          <Card key={e.product.id}>
            <Row>{e.product.imageUrl ? <Image source={{ uri: e.product.imageUrl }} style={{ width: 60, height: 60, borderRadius: 14, backgroundColor: '#fff' }} resizeMode="contain" /> : null}
              <View style={{ flex: 1 }}><Text style={{ color: c.ink, fontWeight: '700', fontSize: 16 }}>{i === 0 ? '★ ' : ''}{e.product.name}</Text><Muted small>{e.product.brand}</Muted></View></Row>
            <Row wrap style={{ marginTop: 8 }}><NutriScore grade={e.product.nutriScore} /><NovaBadge group={e.product.novaGroup} estimated={e.product.novaEstimated} />{e.estimated ? <Pill tone="w">{t('est.pill')}</Pill> : null}{e.dominated ? <Pill tone="g">{t('simple.dominated')}</Pill> : null}</Row>
            {sv > 0 ? <Text style={{ color: c.accent, fontSize: 24, fontWeight: '800', marginTop: 8 }}>−{eur(sv / 100)} <Text style={{ fontSize: 14, fontWeight: '500' }}>{t('simple.perPack')}</Text></Text>
              : e.price100 != null ? <Text style={{ color: c.ink, fontSize: 18, fontWeight: '700', marginTop: 8 }}>{eur(e.price100 / 100 * 10)} / kg</Text> : null}
            <Text style={{ color: c.ink, marginTop: 6 }}>{e.why || '—'}.</Text>
            <Collapsible title={t('simple.moreInfo')}>
              <Muted small>{t('alt.tradeoffs')} : {e.tradeoffs.join(' ; ')}.</Muted>
              {e.sizes > 0 ? <Muted small>{t('simple.sizes', { n: e.sizes })}</Muted> : null}
              {expl[e.product.id]?.text ? <Card tint><Text style={{ color: c.ink }}>{expl[e.product.id].text}</Text><Muted small>{expl[e.product.id].source === 'llm' ? t('ex.llm') : t('ex.template')}</Muted></Card> : <Button small plain onPress={() => explain(e.product.id)}>{expl[e.product.id]?.loading ? t('ex.loading') : t('ex.button')}</Button>}
              <Row wrap><Button small onPress={() => go(routes.product(e.product.id))}>{t('home.explore')}</Button><Button small plain onPress={() => { addCompare(barcode!); addCompare(e.product.id); go(routes.compare); }}>{t('tabs.compare')}</Button></Row>
            </Collapsible>
            {sv > 0 && !chosen.includes(e.product.id) && <Button primary onPress={async () => { await api.chooseSaving({ original_id: barcode!, alt_id: e.product.id, expected_saving_cents: sv, original_per100_cents: r.original_price.per100_cents }); setChosen((x) => [...x, e.product.id]); hx.success(); setNote(t('sav.chosenDone')); setTimeout(() => setNote(null), 2000); }}>{t('sav.buy')}</Button>}
          </Card>);
      })}
      <Toast text={note} />
    </Screen>
  );
}
