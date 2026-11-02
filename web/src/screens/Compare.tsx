import { useEffect, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useProfile, useHistory } from '@shared/stores';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Section, Group, Cell, NutriScore, NovaBadge, Loader } from '../ui';
import { routes, useNav } from '../nav';

/* eslint-disable @typescript-eslint/no-explicit-any */
const LABEL: Record<string, string> = { energyKcal100g: 'kcal', protein100g: 'protein', sugars100g: 'sugars', saturatedFat100g: 'sat', salt100g: 'salt', fiber100g: 'fibre' };

export default function Compare() {
  const { go } = useNav();
  const { compare, addCompare, removeCompare, clearCompare, estimates } = useProfile();
  const addComparison = useHistory((s) => s.addComparison);
  const [r, setR] = useState<any>(null);
  // most recent distinct scans first (stored on this device); a product scanned ten times appears once
  const scans = useHistory((s) => s.scans);
  const recent = scans.map((x) => x.product).filter((p, i, a) => a.findIndex((q) => q.id === p.id) === i);
  useEffect(() => { if (compare.length >= 2) api.compareProducts(compare, estimates).then((x: any) => { setR(x); addComparison(compare, x.products.map((p: any) => p.name)); }).catch(() => setR(null)); else setR(null); }, [compare, estimates]);
  return (
    <Screen>
      <NavBar title={t('compare.title')} />
      <LargeTitle>{t('compare.title')}</LargeTitle>
      {compare.length < 2 && <Card><Muted>{t('compare.empty')}</Muted></Card>}
      {compare.length >= 2 && !r && <Loader />}
      {r && (
        <Card>
          <div style={{ overflowX: 'auto' }}>
            <table><tbody>
              <tr><th />{r.products.map((p: any) => <th key={p.id}>{p.name.slice(0, 18)}<br /><Button small plain onPress={() => removeCompare(p.id)}>{t('compare.remove')}</Button></th>)}</tr>
              <tr><td>{t('compare.nutriscore')}</td>{r.products.map((p: any) => <td key={p.id}><NutriScore grade={p.nutriScore} /></td>)}</tr>
              <tr><td>{t('compare.perKg')}</td>{r.products.map((p: any) => <td key={p.id}>{p.price ? <><b>{(p.price.per100_cents / 10).toFixed(2).replace('.', ',')} €</b>{p.price.source === 'estimate' && <><br /><span className="pill w">{t('est.pill')}</span></>}</> : '—'}</td>)}</tr>
              <tr><td>{t('compare.pack')}</td>{r.products.map((p: any) => <td key={p.id}>{p.price?.pack_cents != null ? (p.price.pack_cents / 100).toFixed(2).replace('.', ',') + ' €' : '—'}</td>)}</tr>
              <tr><td>{t('nova.title').split(' (')[0]}</td>{r.nova.map((g: number | null, i: number) => <td key={i}><NovaBadge group={g} /></td>)}</tr>
              {r.rows.map((row: any) => (
                <tr key={row.field}><td>{t('compare.' + LABEL[row.field])}</td>{row.values.map((v: number | null, i: number) => <td key={i} className={row.favourable[i] ? 'best' : ''}>{v == null ? '—' : Math.round(v * 10) / 10}</td>)}</tr>
              ))}
            </tbody></table>
          </div>
          {r.micro.length > 0 && <><h3 style={{ marginTop: 14 }}>{t('micro.title')}</h3><div style={{ overflowX: 'auto' }}><table><tbody>
            {r.micro.map((m: any) => <tr key={m.key}><td>{t('micro.' + m.key)}</td>{m.values.map((v: number | null, i: number) => <td key={i} className={m.favourable[i] ? 'best' : ''}>{v == null ? '—' : `${v} ${m.unit} (${m.nrv_pct[i]}%)`}</td>)}</tr>)}
          </tbody></table></div><p className="mut sm">{t('micro.note')}</p></>}
          <p className="mut sm">{t('compare.note')}</p>
          <Button small plain danger onPress={clearCompare}>{t('compare.clear')}</Button>
        </Card>
      )}
      <Button primary onPress={() => go(routes.scan, { compare: true })}>{t('compare.scanAnother')}</Button>
      <Section title={t('compare.pickRecent')}>
        {recent.filter((p) => !compare.includes(p.id)).length
          ? <Group>{recent.filter((p) => !compare.includes(p.id)).slice(0, 10).map((p) => (
            <Cell key={p.id} image={p.imageUrl ?? ''} onPress={() => addCompare(p.id)}><b>{p.name}</b><Muted>{[p.brand, p.score ? `${p.score.total}/100` : null].filter(Boolean).join(' · ')}</Muted></Cell>
          ))}</Group>
          : <Card><Muted>{t('compare.noRecent')}</Muted></Card>}
      </Section>
    </Screen>
  );
}
