import { useCallback, useEffect, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { Button, Card, Cell, Group, LargeTitle, Muted, NovaBadge, NutriScore, Screen, Section, Skeleton, useTheme } from '../../src/ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const LABEL: Record<string, string> = { energyKcal100g: 'kcal', protein100g: 'protein', sugars100g: 'sugars', saturatedFat100g: 'sat', salt100g: 'salt', fiber100g: 'fibre' };
export default function Compare() {
  const c = useTheme();
  const { compare, addCompare, removeCompare, clearCompare, estimates } = useProfile();
  const scans = useHistory((s) => s.scans);
  const [r, setR] = useState<any>(null);
  useFocusEffect(useCallback(() => { if (compare.length >= 2) api.compareProducts(compare, estimates).then(setR).catch(() => setR(null)); else setR(null); }, [compare, estimates]));
  useEffect(() => { if (compare.length < 2) setR(null); }, [compare]);
  const cell = (s: string, best?: boolean) => <Text key={s + Math.random()} style={{ width: 96, padding: 6, color: best ? c.accent : c.ink, fontWeight: best ? '700' : '400' }}>{s}</Text>;
  return (
    <Screen>
      <LargeTitle>{t('compare.title')}</LargeTitle>
      {compare.length < 2 && <Card><Muted>{t('compare.empty')}</Muted></Card>}
      {compare.length >= 2 && !r && <Skeleton h={200} />}
      {r && (<Card><ScrollView horizontal><View>
        <View style={{ flexDirection: 'row' }}>{cell('')}{r.products.map((p: any) => <Text key={p.id} style={{ width: 96, padding: 6, color: c.ink, fontWeight: '600' }} numberOfLines={2}>{p.name}</Text>)}</View>
        <View style={{ flexDirection: 'row' }}>{cell(t('compare.perKg'))}{r.products.map((p: any) => cell(p.price ? `${(p.price.per100_cents / 10).toFixed(2).replace('.', ',')} €${p.price.source === 'estimate' ? ' ~' : ''}` : '—'))}</View>
        <View style={{ flexDirection: 'row' }}>{cell(t('compare.nutriscore'))}{r.products.map((p: any) => <View key={p.id} style={{ width: 96, padding: 6 }}><NutriScore grade={p.nutriScore} /></View>)}</View>
        <View style={{ flexDirection: 'row' }}>{cell('NOVA')}{r.nova.map((g: number | null, i: number) => <View key={i} style={{ width: 96, padding: 6 }}><NovaBadge group={g} /></View>)}</View>
        {r.rows.map((row: any) => <View key={row.field} style={{ flexDirection: 'row' }}>{cell(t('compare.' + LABEL[row.field]))}{row.values.map((v: number | null, i: number) => cell(v == null ? '—' : String(Math.round(v * 10) / 10), row.favourable[i]))}</View>)}
      </View></ScrollView><Muted small>{t('compare.note')}</Muted><Button small plain danger onPress={clearCompare}>{t('compare.clear')}</Button></Card>)}
      {compare.length > 0 && <Group>{compare.map((id, i) => <Cell key={id} last={i === compare.length - 1} onPress={() => removeCompare(id)}><Text style={{ color: c.ink }}>{scans.find((s) => s.id === id)?.product.name ?? id}  ·  {t('compare.remove')}</Text></Cell>)}</Group>}
      <Section title={t('compare.pickRecent')}><Group>{scans.filter((s) => !compare.includes(s.id)).slice(0, 10).map((s, i, a) => <Cell key={s.id} last={i === a.length - 1} onPress={() => addCompare(s.id)}><Text style={{ color: c.ink, fontWeight: '600' }}>{s.product.name}</Text><Muted small>+ {t('compare.add')}</Muted></Cell>)}</Group></Section>
    </Screen>
  );
}
