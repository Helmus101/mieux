import { useEffect, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { Button, Card, Muted, Segmented } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const STYLES = ['stay', 'balanced', 'nutrition'];
export default function BudgetForm({ initial, onSaved, compact }: { initial?: any; onSaved?: () => void; compact?: boolean }) {
  const [period, setPeriod] = useState(initial?.period ?? 'weekly');
  const [amount, setAmount] = useState(initial ? String(initial.amount_cents / 100) : '');
  const [style, setStyle] = useState(initial?.style ?? 'balanced');
  const [goal, setGoal] = useState(initial?.savings_goal_cents ? String(initial.savings_goal_cents / 100) : '');
  const [cats, setCats] = useState<Record<string, string>>(Object.fromEntries(Object.entries(initial?.categories ?? {}).map(([k, v]) => [k, String((v as number) / 100)])));
  const [err, setErr] = useState('');
  useEffect(() => { if (initial) { setPeriod(initial.period); setAmount(String(initial.amount_cents / 100)); setStyle(initial.style); setGoal(initial.savings_goal_cents ? String(initial.savings_goal_cents / 100) : ''); setCats(Object.fromEntries(Object.entries(initial.categories ?? {}).map(([k, v]) => [k, String((v as number) / 100)]))); } }, [initial]);
  const euros = (s: string) => Math.round(parseFloat(s.replace(',', '.')) * 100);
  const save = async () => {
    const a = euros(amount);
    if (!a || a <= 0) { setErr(t('pricedb.invalid')); return; }
    await api.putBudget({ period, amount_cents: a, style, savings_goal_cents: goal ? euros(goal) : null, categories: Object.fromEntries(Object.entries(cats).filter(([, v]) => v && euros(v) > 0).map(([k, v]) => [k, euros(v)])) } as never);
    setErr(''); onSaved?.();
  };
  return (
    <div>
      <Segmented value={period} onChange={setPeriod} options={[{ key: 'weekly', label: t('bud.weekly') }, { key: 'monthly', label: t('bud.monthly') }, { key: 'per_trip', label: t('bud.per_trip') }]} />
      <div className="field card" style={{ margin: '8px 0' }}><Muted>{t('bud.amount')}</Muted><input inputMode="decimal" value={amount} placeholder="100" onChange={(e) => setAmount(e.target.value)} /></div>
      <Muted>{t('bud.style')}</Muted>
      {STYLES.map((k) => (
        <button key={k} className={'opt' + (style === k ? ' on' : '')} onClick={() => setStyle(k)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 12, background: 'var(--card)', border: '2px solid ' + (style === k ? 'var(--accent)' : 'transparent'), borderRadius: 14, padding: 14, margin: '6px 0', textAlign: 'left', cursor: 'pointer' }}>
          <b style={{ fontWeight: 500 }}>{t('bud.' + k)}</b>
        </button>
      ))}
      {!compact && <div className="field card" style={{ margin: '8px 0' }}><Muted>{t('bud.goal')}</Muted><input inputMode="decimal" value={goal} placeholder="30" onChange={(e) => setGoal(e.target.value)} /></div>}
      {!compact && <details style={{ margin: '8px 0' }}><summary><b>{t('fc.catTitle')}</b></summary><p className="mut sm">{t('fc.catHint')}</p>
        {['dairy', 'meat_fish', 'fruit_veg', 'bakery_cereals', 'snacks_sweets', 'drinks'].map((g) => <div className="field card" key={g} style={{ margin: '6px 0' }}><Muted>{t('grp.' + g)}</Muted><input inputMode="decimal" placeholder="—" value={cats[g] ?? ''} onChange={(e) => setCats({ ...cats, [g]: e.target.value })} /></div>)}</details>}
      {err && <p style={{ color: 'var(--bad)' }}>{err}</p>}
      <Card tint><Muted>{t('bud.config')}</Muted><b style={{ fontSize: 24 }}>{amount || '—'} €</b> <span className="mut">{t('bud.' + period)}</span></Card>
      <Button primary onPress={save}>{t('bud.save')}</Button>
    </div>
  );
}
