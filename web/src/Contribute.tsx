import { friendlyError } from './errors';
import { useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { Button, Muted, Pill, haptic } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
const NUM: [string, string][] = [['fvn_pct', 'add2.veg'], ['protein_100g', 'add2.protein'], ['fiber_100g', 'add2.fibre'], ['sugars_100g', 'add2.sugars'], ['salt_100g', 'add2.salt']];

/** Let the user complete a product whose database record is missing data (ingredients, vegetable share, protein, fibre...). Saved for them only; the score is recomputed. */
export default function Contribute({ barcode, mine, onChange }: { barcode: string; mine: string[]; onChange: (product: any) => void }) {
  const [vals, setVals] = useState<Record<string, string>>({}), [ing, setIng] = useState(''), [busy, setBusy] = useState(false), [msg, setMsg] = useState('');
  const save = async () => {
    const data: Record<string, unknown> = {};
    NUM.forEach(([k]) => { const v = parseFloat((vals[k] ?? '').replace(',', '.')); if (!Number.isNaN(v)) data[k] = v; });
    if (ing.trim()) data.ingredients_text = ing.trim();
    if (!Object.keys(data).length) return;
    setBusy(true); setMsg('');
    try { const r = await api.contribute(barcode, data); haptic('success'); onChange(r.product); setMsg(t('add2.saved')); setVals({}); setIng(''); }
    catch (e: any) { haptic('error'); const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); }
    setBusy(false);
  };
  const reset = async () => { try { await api.clearContribution(barcode); const r = await api.getProduct(barcode); onChange(r.product); } catch (e: any) { const m = friendlyError(e); setMsg(`${m.title} : ${m.why}`); } };
  return (
    <div>
      <Muted>{t('add2.hint')}</Muted>
      {mine.length > 0 && <p><Pill>{t('add2.mine')}</Pill> <span className="mut sm">{mine.join(', ')}</span></p>}
      <textarea rows={3} value={ing} onChange={(e) => setIng(e.target.value)} placeholder={t('add2.ing')} />
      {NUM.map(([k, label]) => (
        <div className="field" key={k}><span className="mut" style={{ flex: 1 }}>{t(label)}</span>
          <input style={{ maxWidth: 90, textAlign: 'right' }} inputMode="decimal" value={vals[k] ?? ''} onChange={(e) => setVals((v) => ({ ...v, [k]: e.target.value }))} placeholder="—" /></div>))}
      <Button primary disabled={busy} onPress={save}>{t('add2.save')}</Button>
      {mine.length > 0 && <Button small plain onPress={reset}>{t('add2.reset')}</Button>}
      {msg && <p className="mut sm">{msg}</p>}
    </div>
  );
}
