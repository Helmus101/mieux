import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { additiveInfo } from '@shared/additives';
import { t } from '@shared/i18n';
import { formatCents, isLiquid } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { priceHeadline, verdictOf } from '@shared/verdict';
import { Bar, Button, Card, Collapsible, Muted, NovaBadge, AmountScale, NutriScore, ScoreBar, Pill, Row, Screen, NavBar, Segmented, Sheet, Skeleton } from '../ui';
import { routes, useNav } from '../nav';
import Where from '../Where';

/* eslint-disable @typescript-eslint/no-explicit-any */

const TONE_V: Record<string, string> = { g: 'var(--accent)', g2: '#6fae2e', y: '#b8900a', w: 'var(--warn)', b: 'var(--bad)' };
const toneVar = (tn?: string) => ({ g: 'var(--accent)', g2: '#8bc34a', w: 'var(--warn)', b: 'var(--bad)' } as Record<string, string>)[tn ?? ''] ?? 'var(--ink)';

export default function Product() {
  const { barcode } = useParams<{ barcode: string }>();
  const { go, back } = useNav();
  const estimates = useProfile((s) => s.estimates), addCompare = useProfile((s) => s.addCompare);
  const hist = useHistory();
  const [d, setD] = useState<any>(null), [err, setErr] = useState<{ kind: 'notfound' | 'invalid' | 'server' | 'network'; msg: string } | null>(null), [attempt, setAttempt] = useState(0), [offline, setOffline] = useState(false), [sheet, setSheet] = useState<string | null>(null), [basis, setBasis] = useState<'100' | 'serving' | 'pack'>('100');
  useEffect(() => {
    if (!barcode) return;
    setD(null); setErr(null); setOffline(false);
    api.getProduct(barcode, estimates).then((x: any) => { setD(x); hist.addScan(x.product); api.addScan(barcode).catch(() => undefined); })
      .catch((e: any) => { const snap = useHistory.getState().productById(barcode); if (snap && e?.response?.status !== 404) { setD({ product: snap, fit: [], price_context: null }); setOffline(true); } else setErr(e?.response?.status === 404 ? { kind: 'notfound', msg: '' } : e?.response?.status === 400 ? { kind: 'invalid', msg: '' } : e?.response ? { kind: 'server', msg: e?.response?.data?.detail ?? e.message } : { kind: 'network', msg: e.message }); });
  }, [barcode, estimates, attempt]);
  if (err) return (
    <Screen>
      <NavBar onBack={back} />
      <Card>
        <h2 style={{ margin: '0 0 6px', textTransform: 'none', letterSpacing: 0, fontSize: 22, color: 'var(--ink)' }}>{t(err.kind === 'notfound' ? 'product.nf.title' : err.kind === 'invalid' ? 'product.nf.invalidTitle' : err.kind === 'network' ? 'product.nf.netTitle' : 'product.nf.srvTitle')}</h2>
        {err.kind === 'notfound' && <><p style={{ margin: '4px 0' }}>{t('product.nf.code', { c: barcode ?? '' })}</p><p className="mut sm">{t('product.nf.why')}</p></>}
        {err.kind === 'invalid' && <p className="mut">{t('product.nf.invalid', { c: barcode ?? '' })}</p>}
        {err.kind === 'network' && <p className="mut">{t('net.down')}</p>}
        {err.kind === 'server' && <p className="mut">{t('product.nf.srv')}</p>}
      </Card>
      {(err.kind === 'server' || err.kind === 'network') && <Button primary onPress={() => setAttempt((n) => n + 1)}>{t('common.retry')}</Button>}
      <Button primary={err.kind === 'notfound' || err.kind === 'invalid'} onPress={() => go(routes.scan)}>{t('product.nf.scanAgain')}</Button>
      {err.kind === 'notfound' && <Button plain onPress={() => setAttempt((n) => n + 1)}>{t('common.retry')}</Button>}
    </Screen>
  );
  if (!d) return <Screen><NavBar onBack={back} /><Skeleton h={90} /><Skeleton h={120} /><Skeleton h={60} /></Screen>;

  const p = d.product, pc = d.price_context;
  const liquid = isLiquid(p), per = liquid ? 'ml' : 'g';
  const bases = [{ key: '100', label: t('sdim.per100', { u: per }), f: 1 }, ...(p.servingG ? [{ key: 'serving', label: t('sdim.perServing', { n: Math.round(p.servingG), u: per }), f: p.servingG / 100 }] : []),
    ...(p.quantity?.amount ? [{ key: 'pack', label: t('sdim.perPack', { n: Math.round(p.quantity.amount), u: per }), f: p.quantity.amount / 100 }] : [])];
  const factor = (bases.find((b) => b.key === basis) ?? bases[0]).f;
  const amt = (v: number | null | undefined) => (v == null ? '—' : String(Math.round(v * factor * 10) / 10).replace('.', ','));
  const verdict = verdictOf(d.fit), head = priceHeadline(pc);
  const info = sheet ? additiveInfo(sheet) : null;
  return (
    <Screen>
      <NavBar onBack={back} title={p.name} />
      {offline && <Pill tone="w">{t('history.offline')}</Pill>}
      {p.soldInFrance !== true && <Card><Pill tone="w">{p.soldInFrance === false ? t('simple.notFr') : t('simple.frUnknown')}</Pill></Card>}
      <Row>
        {p.imageUrl && <img src={p.imageUrl} alt="" width={88} height={88} style={{ objectFit: 'contain', borderRadius: 16, background: '#fff' }} />}
        <div><Muted>{p.brand}</Muted><h1 style={{ fontSize: 24 }}>{p.name}</h1><Muted>{p.quantityText}</Muted></div>
      </Row>

      <Card>
        {p.score ? <>
          <Row spread><div className="scorebig" style={{ color: p.score.tone === 'b' ? 'var(--bad)' : p.score.tone === 'w' ? 'var(--warn)' : 'var(--accent)' }}>{p.score.total}<small>{t('score.outOf')}</small></div><span style={{ textAlign: 'right' }}><b>{t('score.' + p.score.band)}</b><br /><span className="mut sm">{t('score.title')}</span></span></Row>
          <ScoreBar total={p.score.total} label={t('score.spectrum')} />
          {p.score.flags?.length > 0 && <div className="flags">{p.score.flags.slice(0, 3).map((f: any) => <span key={f.key} className={'pill ' + (f.level === 'bad' ? 'b' : 'w')}>{t('flag.' + f.key)}</span>)}</div>}
        </> : <Muted>{t('score.na')}</Muted>}
        {head.kind !== 'none' ? <p style={{ margin: '10px 0 0' }}><b>{head.kind === 'estimate' ? '~ ' : ''}{t(isLiquid(p) ? 'simple.perL' : 'simple.perKg', { p: formatCents(head.perKgCents!) })}</b>{head.kind === 'estimate' && <> <Pill tone="w">{t('est.pill')}</Pill></>}</p> : <p className="mut sm" style={{ margin: '10px 0 0' }}>{t('simple.noPrice')}</p>}
        {pc?.community && head.kind === 'real' && <p className="mut sm" style={{ margin: '2px 0 0' }}>{[pc.community.pack_cents != null && p.quantity?.amount ? `${t('size.pack', { s: p.quantity.amount >= 1000 ? `${Math.round(p.quantity.amount / 100) / 10} ${p.quantity.unit === 'ml' ? 'L' : 'kg'}` : `${Math.round(p.quantity.amount)} ${p.quantity.unit}` })} ${formatCents(pc.community.pack_cents)}` : null, pc.community.n_observations ? t('price.reports', { n: pc.community.n_observations, c: pc.community.n_chains ?? 1 }) : null, pc.community.date ? t(pc.community.stale ? 'price.oldAt' : 'price.at', { d: String(pc.community.date).slice(0, 7) }) : null].filter(Boolean).join(' · ')}</p>}
      </Card>
      <Button primary onPress={() => go(routes.alternatives(p.id))}>{t('simple.findBetter')}</Button>
      {p.score && <Collapsible title={t('sdim.title')}>
          {p.score.parts && <p className="mut sm" style={{ margin: '6px 0 0' }}>{p.score.parts.map((x: any) => `${t('score.part_' + x.key)} ${Math.round(x.got)}/${x.of}`).join(' · ')}{p.score.uncapped > p.score.total ? ` · ${t('score.cappedFrom', { a: p.score.uncapped, b: p.score.total })}` : ''}</p>}
        <Row wrap><NutriScore grade={p.nutriScore} />{verdict && <span className="mut sm"><span className={'dot ' + (verdict.tone ?? 'g')} />{verdict.text}</span>}</Row>
          <p className="mut sm">{t('sdim.profile', { x: t('prof.' + p.score.profile) })} · {t('sdim.confidence', { x: t('sdim.conf_' + p.score.confidence.level), p: p.score.confidence.pct })}{p.score.incomplete ? ' · ' + t('sdim.incomplete') : ''}</p>
          <div className="nsec">{t('sdim.amountsFor')}</div>
          {bases.length > 1 ? <Segmented value={basis} onChange={(k) => setBasis(k as any)} options={bases.map((b) => ({ key: b.key, label: b.label }))} /> : <p className="mut sm">{bases[0].label}</p>}
          <div className="trio">
            <div><span className="mut sm">{t('sdim.nutritional')}</span><b style={{ color: toneVar(p.score.nutritional.tone) }}>{p.score.nutritional.score}</b></div>
            <div><span className="mut sm">{t('sdim.ingredient')}</span><b style={{ color: toneVar(p.score.ingredient?.tone) }}>{p.score.ingredient ? p.score.ingredient.score : '—'}</b></div>
            <div><span className="mut sm">{t('sdim.processing')}</span><NovaBadge group={p.novaGroup} estimated={p.novaEstimated} /></div>
          </div>
          {p.score.caps?.length > 0 && <p className="mut sm">{p.score.caps.map((c: string) => t('cap.' + c)).join(' ')}</p>}
          {(['nutrition', 'ingredients'] as const).map((g) => (
            <div key={g}>
              <div className="nsec">{t('sdim.grp_' + g)}</div>
              {p.score.dimensions.filter((d: any) => d.group === g).map((d: any) => (
                <div className="nrow" key={d.key}>
                  <div className="nrow-top"><span>{t('sdim.' + d.key)}</span>
                    {d.scale ? <span><b>{d.key === 'plant' ? d.scale.value : amt(d.scale.value)} {d.scale.unit}</b>{d.scale.estimated && <span className="mut sm"> ({t('add2.est')})</span>} <span className="mut sm" style={{ color: TONE_V[d.scale.tone] }}>{t((d.scale.better === 'more' ? 'tierPos.' : 'tier.') + d.scale.tier)}</span></span>
                      : !d.relevant ? <span className="mut">{t('sdim.na')}</span> : d.missing ? <span className="mut">{t('sdim.missing')}</span>
                      : <span className="mut sm" style={{ color: TONE_V[d.tone] }}>{d.key === 'micro' ? t('sdim.microList', { n: (d.detail.rich?.length ?? 0) + (d.detail.source?.length ?? 0) }) : t('tier.' + (d.score >= 75 ? 'excellent' : d.score >= 50 ? 'good' : d.score >= 25 ? 'poor' : 'bad'))}</span>}</div>
                  {d.scale && <AmountScale scale={d.scale} />}
                  {d.key === 'fat' && d.detail?.sat != null && <p className="mut sm">{t('sdim.fatDetail', { s: amt(d.detail.sat), f: amt(d.detail.total) })}{d.detail.trans != null ? ' · ' + t('sdim.trans', { x: amt(d.detail.trans) }) : ''}</p>}
                </div>))}
            </div>))}
          {p.score.sugar && (() => {
            const g = p.score.sugar, k = g.kind;
            return <div className="sugarbox">
              <b>{t('nut.sugarTitle')} : {g.total} g</b>
              <div className="chips"><span className={'pill ' + (k === 'natural' ? '' : 'g')}>{t('nut.sugarNatural')}</span><span className={'pill ' + (k === 'added' || k === 'mixed' ? 'w' : 'g')}>{t('nut.sugarAdded')}</span></div>
              <p className="mut sm">{k === 'natural' ? t('nut.sugarNaturalNote') : k === 'added' ? t('nut.sugarAddedNote', { x: g.added.join(', ') }) : k === 'mixed' ? t('nut.sugarMixedNote', { x: g.added.join(', ') }) : k === 'none' ? t('nut.sugarNone') : t('nut.sugarUnknown')}</p>
            </div>;
          })()}
          <div className="nsec">{t('nut.addTitle')}</div>
          {p.score.additives.items.length ? p.score.additives.items.map((a: any) => <div className="nrow" key={a.code}><div className="nrow-top"><span>{a.code.toUpperCase()}{a.name ? ` · ${a.name}` : additiveInfo(a.code) ? ` · ${additiveInfo(a.code)!.name}` : ''}</span><span><span className={'dot ' + ({ A: 'g', B: 'g', C: 'w', D: 'b' } as any)[a.level]} /><b>{a.level}</b> <span className="mut sm">{a.known ? '' : t('sdim.lowEvidence')}</span></span></div><p className="mut sm">{a.note}</p></div>) : <p className="mut sm">{t('nut.addNone')}</p>}
          <p className="mut sm">{t(p.score.mode === 'strict' ? 'score.method3' : 'score.method2')}</p>
      </Collapsible>}

      <Collapsible open title={t('where.title')}><Where barcode={p.id} liquid={isLiquid(p)} /></Collapsible>
      {p.micronutrients?.length > 0 && <Collapsible title={t('simple.microSec')}>
        {p.micronutrients.map((m: any) => <div key={m.key} style={{ margin: '10px 0' }}><Row spread><span>{t('micro.' + m.key)}</span><Muted>{m.amount} {m.unit} · {m.nrv_pct}%</Muted></Row><Bar value={Math.min(1, m.nrv_pct / 100)} /></div>)}
        <p className="mut sm">{t('micro.note')}</p>
      </Collapsible>}
      <Collapsible title={t('simple.ingSec')}>
        <Muted>{p.ingredientsText || t('product.noIng')}</Muted>
        <p>{p.allergens.length ? p.allergens.map((a: string) => <Pill key={a} tone="w">{a}</Pill>) : <span className="mut sm">{p.ingredientsText ? t('product.allergenNone') : t('product.allergenMissing')}</span>}</p>
        <a target="_blank" rel="noreferrer" href={`https://world.openfoodfacts.org/product/${p.id}`}>{t('product.correct')}</a>
      </Collapsible>
      <a target="_blank" rel="noreferrer" href={`https://world.openfoodfacts.org/product/${p.id}`}>{t('score.page')}</a>
      <Button plain onPress={() => { addCompare(p.id); go(routes.compare); }}>{t('product.compare')}</Button>

      <Sheet open={!!sheet} onClose={() => setSheet(null)} title={sheet ? sheet.toUpperCase() + (info ? ' · ' + info.name : '') : ''}>
        {info ? <><h3>{t('add.why')}</h3><p>{info.why}</p><h3>{t('add.evidence')}</h3><p>{info.evidence}</p><h3>{t('add.regulation')}</h3><p>{info.regulation}</p><h3>{t('add.advice')}</h3><p>{info.advice}</p>
          <p className="mut sm">{t('add.source')} : <a target="_blank" rel="noreferrer" href={info.source}>EFSA / UE</a></p></> : <><p className="mut">{t('add.unknown')}</p><a target="_blank" rel="noreferrer" href="https://food.ec.europa.eu/food-safety/food-improvement-agents/additives/database_en">{t('add.euDb')}</a></>}
        <Button onPress={() => setSheet(null)}>{t('common.done')}</Button>
      </Sheet>
    </Screen>
  );
}
