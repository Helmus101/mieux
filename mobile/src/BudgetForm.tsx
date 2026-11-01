import { useState } from 'react';
import { Pressable, Text } from 'react-native';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { Button, Card, Field, Muted, Segmented, useTheme } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function BudgetForm({ initial, onSaved, compact }: { initial?: any; onSaved?: () => void; compact?: boolean }) {
  const c = useTheme();
  const [period, setPeriod] = useState<string>(initial?.period ?? 'weekly');
  const [amount, setAmount] = useState(initial ? String(initial.amount_cents / 100) : '');
  const [style, setStyle] = useState<string>(initial?.style ?? 'balanced');
  const [goal, setGoal] = useState(initial?.savings_goal_cents ? String(initial.savings_goal_cents / 100) : '');
  const [err, setErr] = useState('');
  const euros = (s: string) => Math.round(parseFloat(s.replace(',', '.')) * 100);
  const save = async () => {
    const a = euros(amount);
    if (!a || a <= 0) { setErr(t('pricedb.invalid')); return; }
    await api.putBudget({ period, amount_cents: a, style, savings_goal_cents: goal ? euros(goal) : null, categories: initial?.categories });
    setErr(''); onSaved?.();
  };
  return (
    <>
      <Segmented value={period} onChange={setPeriod} options={[{ key: 'weekly', label: t('bud.weekly') }, { key: 'monthly', label: t('bud.monthly') }, { key: 'per_trip', label: t('bud.per_trip') }]} />
      <Muted>{t('bud.amount')}</Muted><Field value={amount} onChangeText={setAmount} placeholder="100" numeric />
      <Muted>{t('bud.style')}</Muted>
      {['stay', 'balanced', 'nutrition'].map((k) => (
        <Pressable key={k} onPress={() => setStyle(k)} style={{ backgroundColor: c.card, borderRadius: 14, padding: 14, marginVertical: 5, borderWidth: 2, borderColor: style === k ? c.accent : 'transparent' }}><Text style={{ color: c.ink }}>{t('bud.' + k)}</Text></Pressable>))}
      {!compact && <><Muted>{t('bud.goal')}</Muted><Field value={goal} onChangeText={setGoal} placeholder="30" numeric /></>}
      {err ? <Text style={{ color: c.bad }}>{err}</Text> : null}
      <Card tint><Muted>{t('bud.config')}</Muted><Text style={{ color: c.ink, fontSize: 22, fontWeight: '700' }}>{amount || '—'} € · {t('bud.' + period)}</Text></Card>
      <Button primary onPress={save}>{t('bud.save')}</Button>
    </>
  );
}
