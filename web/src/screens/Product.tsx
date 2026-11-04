import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { additiveInfo } from '@shared/additives';
import { t } from '@shared/i18n';
import { formatCents, isLiquid } from '@shared/utils/format';
import { useHistory, useProfile } from '@shared/stores';
import { priceHeadline } from '@shared/verdict';
import { haptic } from '../ui';
import { Bar, Button, Card, Collapsible, Muted, NovaBadge, AmountScale, NutriScore, ScoreBar, Pill, Row, Screen, NavBar, Segmented, Sheet, Skeleton, Loader } from '../ui';
import { routes, useNav } from '../nav';
import Where from '../Where';
import { InstallCard } from '../InstallPrompt';
import DesktopQRBanner from '../DesktopQRBanner';
import { countScan } from '../account';

/* eslint-disable @typescript-eslint/no-explicit-any */

const TONE_V: Record<string, string> = { g: 'var(--accent)', g2: 'var(--olive)', y: 'var(--clay)', w: 'var(--warn)', b: 'var(--bad)' };
const toneVar = (tn?: string) => ({ g: 'var(--accent)', g2: 'var(--olive)', w: 'var(--warn)', b: 'var(--bad)' } as Record<string, string>)[tn ?? ''] ?? 'var(--ink)';

export default function Product() {
  const { barcode } = useParams<{ barcode: string }>();
  const { go, back } = useNav();
  const estimates = useProfile((s) => s.estimates), addCompare = useProfile((s) => s.addCompare);
  const priorities = useProfile((s) => s.priorities);
  const hist = useHistory();
  const [d, setD] = useState<any>(null), [err, setErr] = useState<{ kind: 'notfound' | 'notfood' | 'invalid' | 'server' | 'network'; msg: string } | null>(null), [attempt, setAttempt] = useState(0), [offline, setOffline] = useState(false), [sheet, setSheet] = useState<string | null>(null), autoTries = useRef(0), [basis, setBasis] = useState<'100' | 'serving' | 'pack'>('100');
  useEffect(() => {
    if (!barcode) return;
    setD(null); setErr(null); setOffline(false);
    let cancelled = false, retryTimer: ReturnType<typeof setTimeout> | undefined;
    api.getProduct(barcode, estimates).then((x: any) => { setD(x); hist.addScan(x.product); api.addScan(barcode).catch(() => undefined); countScan(barcode); })
      .catch((e: any) => { if (!cancelled && autoTries.current < 2 && e?.response?.status !== 400 && !(e?.response && ![404, 502, 503, 504].includes(e.response.status))) { autoTries.current += 1; retryTimer = setTimeout(() => setAttempt((n) => n + 1), 1200); return; } const snap = useHistory.getState().productById(barcode); if (snap && e?.response?.status !== 404) { setD({ product: snap, fit: [], price_context: null }); setOffline(true); } else setErr(e?.response?.status === 404 ? { kind: e.response.data?.detail === 'not_food' ? 'notfood' : 'notfound', msg: '' } : e?.response?.status === 400 ? { kind: 'invalid', msg: '' } : e?.response ? { kind: 'server', msg: e?.response?.data?.detail ?? e.message } : { kind: 'network', msg: e.message }); });
    return () => { cancelled = true; if (retryTimer) clearTimeout(retryTimer); };
  }, [barcode, estimates, attempt]);
  useEffect(() => { autoTries.current = 0; }, [barcode]);
  if (err) return (
    <Screen>
      <NavBar onBack={back} />
      <Card>
        <h2 style={{ margin: '0 0 6px', textTransform: 'none', letterSpacing: 0, fontSize: 22, color: 'var(--ink)' }}>{t(err.kind === 'notfood' ? 'product.nf.foodTitle' : err.kind === 'notfound' ? 'product.nf.title' : err.kind === 'invalid' ? 'product.nf.invalidTitle' : err.kind === 'network' ? 'product.nf.netTitle' : 'product.nf.srvTitle')}</h2>
        {err.kind === 'notfound' && <><p style={{ margin: '4px 0' }}>{t('product.nf.code', { c: barcode ?? '' })}</p><p className="mut sm">{t('product.nf.why')}</p></>}
        {err.kind === 'notfood' && <p className="mut">{t('product.nf.food')}</p>}
        {err.kind === 'invalid' && <p className="mut">{t('product.nf.invalid', { c: barcode ?? '' })}</p>}
        {err.kind === 'network' && <p className="mut">{t('net.down')}</p>}
        {err.kind === 'server' && <p className="mut">{t('product.nf.srv')}</p>}
      </Card>
      {(err.kind === 'server' || err.kind === 'network') && <Button primary onPress={() => setAttempt((n) => n + 1)}>{t('common.retry')}</Button>}
      <Button primary={err.kind === 'notfound' || err.kind === 'notfood' || err.kind === 'invalid'} onPress={() => go(routes.scan)}>{t('product.nf.scanAgain')}</Button>
      {err.kind === 'notfound' && <Button plain onPress={() => setAttempt((n) => n + 1)}>{t('common.retry')}</Button>}
    </Screen>
  );
  if (!d) return <Screen><NavBar onBack={back} /><Loader steps={t('common.stepsProduct').split('|')} onRetry={() => setAttempt((n) => n + 1)} /><Skeleton h={90} /><Skeleton h={120} /></Screen>;

  const p = d.product, pc = d.price_context;
  const liquid = isLiquid(p), per = liquid ? 'ml' : 'g';
  const bases = [{ key: '100', label: t('sdim.per100', { u: per }), f: 1 }, ...(p.servingG ? [{ key: 'serving', label: t('sdim.perServing', { n: Math.round(p.servingG), u: per }), f: p.servingG / 100 }] : []),
    ...(p.quantity?.amount ? [{ key: 'pack', label: t('sdim.perPack', { n: Math.round(p.quantity.amount), u: per }), f: p.quantity.amount / 100 }] : [])];
  const factor = (bases.find((b) => b.key === basis) ?? bases[0]).f;
  const amt = (v: number | null | undefined) => (v == null ? '—' : String(Math.round(v * factor * 10) / 10).replace('.', ','));
  const head = priceHeadline(pc);
  const info = sheet ? additiveInfo(sheet) : null;
  const sItem = sheet ? ((p.score?.additives?.items ?? []) as any[]).find((x) => x.code === sheet) : null;
  return (
    <Screen>
      <NavBar onBack={back} title={p.name} />
      {offline && <Pill tone="w">{t('history.offline')}</Pill>}
      {p.soldInFrance !== true && <Card><Pill tone="w">{p.soldInFrance === false ? t('simple.notFr') : t('simple.frUnknown')}</Pill></Card>}
      <Row>
        {p.imageUrl && <img src={p.imageUrl} alt="" decoding="async" fetchPriority="high" width={88} height={88} style={{ objectFit: 'contain', borderRadius: 16, background: '#fff' }} />}
        <div><Muted>{p.brand}</Muted><h1 style={{ fontSize: 24 }}>{p.name}</h1><Muted>{p.quantityText}</Muted></div>
      </Row>

      {(() => {
        const rf = (d.fit ?? []).filter((x: any) => x.priority.startsWith('allergen:') || x.priority.startsWith('diet:'));
        if (!rf.length) return null;
        const key = (x: any) => x.priority.split(':')[1];
        const nm = (x: any) => t((x.priority.startsWith('allergen:') ? 'restr.a_' : 'restr.d_') + key(x));
        const has = rf.filter((x: any) => x.priority.startsWith('allergen:') && x.status === 'conflict' && p.allergens.includes(key(x))).map(nm);
        const tr2 = rf.filter((x: any) => x.priority.startsWith('allergen:') && x.status === 'conflict' && !p.allergens.includes(key(x))).map(nm);
        const dietBad = rf.filter((x: any) => x.priority.startsWith('diet:') && x.status === 'conflict').map(nm);
        const unk = rf.filter((x: any) => x.status === 'unknown').map(nm);
        const lines = [has.length ? t('restr.contains', { x: has.join(', ') }) : '', tr2.length ? t('restr.traces', { x: tr2.join(', ') }) : '', ...dietBad.map((x: string) => t('restr.notDiet', { x })), unk.length ? t('restr.unknown', { x: unk.join(', ') }) : ''].filter(Boolean);
        const bad = has.length + tr2.length + dietBad.length > 0;
        return <Card><div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}><span style={{ fontSize: 22, lineHeight: 1.2, color: bad ? 'var(--bad)' : lines.length ? 'var(--warn)' : 'var(--accent)' }}>{bad ? '✗' : lines.length ? '!' : '✓'}</span>
          <div>{lines.length ? lines.map((l) => <p key={l} style={{ margin: '0 0 4px', fontWeight: 600, color: bad ? 'var(--bad)' : 'var(--ink)' }}>{l}</p>) : <p style={{ margin: '0 0 4px', fontWeight: 600 }}>{t('restr.ok')}</p>}<p className="mut sm" style={{ margin: 0 }}>{t('restr.check')}</p></div></div></Card>;
      })()}
      <Card>
        {p.score ? <>
          <Row spread><div className="scorebig" style={{ color: p.score.tone === 'b' ? 'var(--bad)' : p.score.tone === 'w' ? 'var(--warn)' : 'var(--accent)' }}>{p.score.total}<small>{t('score.outOf')}</small></div><span style={{ textAlign: 'right' }}><b>{t('score.' + p.score.band)}</b><br /><span className="mut sm">{t('score.title')}</span></span></Row>
          <ScoreBar total={p.score.total} label={t('score.spectrum')} />
          {(p.score.additives?.items ?? []).some((x: any) => x.level === 'C' || x.level === 'D') && <div className="flags">{(p.score.additives.items as any[]).filter((x) => x.level === 'C' || x.level === 'D').slice(0, 4).map((x) => <span key={x.code} className={'pill ' + (x.level === 'D' ? 'b' : 'w')} onClick={() => setSheet(x.code)}>{x.code.toUpperCase()}{x.name ? ' · ' + x.name.split(' (')[0] : ''}</span>)}</div>}
          {p.score.incomplete && <div className="flags"><span className="pill g">{t('sdim.incomplete')}</span></div>}
          {p.score.flags?.length > 0 && <div className="flags">{p.score.flags.slice(0, 3).map((f: any) => <span key={f.key} className={'pill ' + (f.level === 'bad' ? 'b' : 'w')}>{t('flag.' + f.key)}</span>)}</div>}
        </> : <Muted>{t('score.na')}</Muted>}
        {head.kind !== 'none' ? <p style={{ margin: '10px 0 0' }}><b>{head.kind === 'estimate' ? '~ ' : ''}{t(isLiquid(p) ? 'simple.perL' : 'simple.perKg', { p: formatCents(head.perKgCents!) })}</b>{head.kind === 'estimate' && <> <Pill tone="w">{t('est.pill')}</Pill></>}</p> : <p className="mut sm" style={{ margin: '10px 0 0' }}>{t('simple.noPrice')}</p>}
      </Card>
      {p.score && priorities.length > 0 && (
        <Card>
          <p className="mut sm" style={{ margin: '0 0 8px' }}>{t('priorities.title')}</p>
          {priorities.map((key) => {
            const aligned = (() => {
              if (key === 'additives') {
                return !(p.score.additives?.items ?? []).some((x: any) => x.level === 'C' || x.level === 'D');
              }
              if (key === 'overall' || key === 'value') {
                return p.score.total >= 50;
              }
              if (key === 'budget') {
                return head.kind !== 'none' && head.perKgCents !== undefined && head.perKgCents < 500;
              }
              if (key === 'sugars') {
                const dim = p.score.dimensions?.find((d: any) => d.key === 'sugars');
                return dim && dim.score >= 50;
              }
              if (key === 'protein') {
                const dim = p.score.dimensions?.find((d: any) => d.key === 'protein');
                return dim && dim.score >= 50;
              }
              if (key === 'fibre') {
                const dim = p.score.dimensions?.find((d: any) => d.key === 'fibre');
                return dim && dim.score >= 50;
              }
              return true;
            })();
            return (
              <div key={key} style={{ display: 'flex', alignItems: 'center', padding: '8px 0' }}>
                <span style={{ 
                  marginRight: 12, 
                  fontSize: 18,
                  color: aligned ? 'var(--accent)' : 'var(--bad)'
                }}>{aligned ? '✓' : '✗'}</span>
                <span style={{ flex: 1 }}>{t('priorities.' + key)}</span>
              </div>
            );
          })}
        </Card>
      )}
      <Button primary onPress={() => go(routes.alternatives(p.id))}>{t('simple.findBetter')}</Button>
      {p.score && <Collapsible open={false} title={t('sdim.title')}>
          {p.score.parts && <p className="mut sm" style={{ margin: '6px 0 0' }}>{p.score.parts.map((x: any) => `${t('score.part_' + x.key)} ${Math.round(x.got)}/${x.of}`).join(' · ')}{p.score.uncapped > p.score.total ? ` · ${t('score.cappedFrom', { a: p.score.uncapped, b: p.score.total })}` : ''}</p>}
        <Row wrap><NutriScore grade={p.nutriScore} /></Row>
          <p className="mut sm">{t('sdim.profile', { x: t('prof.' + p.score.profile) })} · {t('sdim.confidence', { x: t('sdim.conf_' + p.score.confidence.level), p: p.score.confidence.pct })}{p.score.incomplete ? ' · ' + t('sdim.incomplete') : ''}</p>
          <div className="nsec">{t('sdim.amountsFor')}</div>
          {bases.length > 1 ? <Segmented value={basis} onChange={(k) => setBasis(k as any)} options={bases.map((b) => ({ key: b.key, label: b.label }))} /> : <p className="mut sm">{bases[0].label}</p>}
          <div className="trio">
            <div><span className="mut sm">{t('sdim.nutritional')}</span><b style={{ color: toneVar(p.score.nutritional.tone) }}>{p.score.nutritional.score}</b></div>
            <div><span className="mut sm">{t('sdim.ingredient')}</span><b style={{ color: toneVar(p.score.ingredient?.tone) }}>{p.score.ingredient ? p.score.ingredient.score : '—'}</b></div>
            <div><span className="mut sm">{t('sdim.processing')}</span><NovaBadge group={p.novaGroup} estimated={p.novaEstimated} /></div>
          </div>
          {p.score.caps?.length > 0 && <p className="mut sm">{p.score.caps.map((c: string) => t('cap.' + c)).join(' ')}</p>}
          <div className="nsec">{t('sdim.grp_nutrition')}</div>
          {p.score.dimensions.filter((d: any) => d.group === 'nutrition' && d.relevant && !d.missing).map((d: any) => {
            const sg = d.key === 'sugar' ? p.score.sugar : null, sk = sg?.kind;
            return (
              <div className="nrow" key={d.key}>
                <div className="nrow-top"><span>{t('sdim.' + d.key)}{sk === 'natural' && <span className="tag nat">{t('nut.sugarNatural')}</span>}{(sk === 'added' || sk === 'mixed') && <span className="tag add">{t('nut.sugarAdded')}</span>}</span>
                  {d.scale ? <span><b>{d.key === 'plant' ? d.scale.value : amt(d.scale.value)} {d.scale.unit}</b>{d.scale.estimated && <span className="mut sm"> ({t('add2.est')})</span>} <span className="mut sm" style={{ color: TONE_V[d.scale.tone] }}>{t((d.scale.better === 'more' ? 'tierPos.' : 'tier.') + d.scale.tier)}</span></span>
                    : <span className="mut sm" style={{ color: TONE_V[d.tone] }}>{d.key === 'micro' ? t('sdim.microList', { n: (d.detail.rich?.length ?? 0) + (d.detail.source?.length ?? 0) }) : t('tier.' + (d.score >= 75 ? 'excellent' : d.score >= 50 ? 'good' : d.score >= 25 ? 'poor' : 'bad'))}</span>}</div>
                {d.scale && <AmountScale scale={d.scale} />}
                {sg && (sk === 'added' || sk === 'mixed') && sg.added?.length > 0 && <p className="mut sm">{t('nut.sugarAddedNote', { x: sg.added.join(', ') })}</p>}
                {d.key === 'fat' && d.detail?.sat != null && <p className="mut sm">{t('sdim.fatDetail', { s: amt(d.detail.sat), f: amt(d.detail.total) })}{d.detail.trans != null ? ' · ' + t('sdim.trans', { x: amt(d.detail.trans) }) : ''}</p>}
              </div>);
          })}
          <p className="mut sm">{t(p.score.mode === 'strict' ? 'score.method3' : 'score.method2')}</p>
      </Collapsible>}

      {p.score && (() => {
        const all = [...(p.score.additives?.items ?? [])] as any[];
        const items = all.filter((x) => x.known || !all.some((o) => o !== x && x.code.startsWith(o.code))).sort((x, y) => y.level.localeCompare(x.level) || x.code.localeCompare(y.code));
        const risky = items.filter((x) => x.level === 'C' || x.level === 'D');
        return <Collapsible open={false} title={`${t('addl.title')} · ${items.length ? t('addl.count', { n: items.length }) + (risky.length ? ' · ' + t('addl.bad', { n: risky.length }) : '') : t('addl.none')}`}>
          {items.length === 0 && <p className="mut">{t('addl.none')}</p>}
          {items.map((a: any) => {
            const hi = a.level === 'C' || a.level === 'D';
            const nm = a.name || additiveInfo(a.code)?.name || '';
            return <div className="risk" key={a.code} onClick={() => { haptic('tap'); setSheet(a.code); }} style={{ cursor: 'pointer' }}>
              <div className="addhead"><span className={'dot ' + (a.level === 'D' ? 'b' : a.level === 'C' ? 'w' : 'g')} /><b>{a.code.toUpperCase()}</b><span className="addname">{nm}</span><span className="chev">›</span></div>
              {hi && a.note && <p className="mut sm">{a.note}</p>}
            </div>;
          })}
        </Collapsible>;
      })()}
      <Collapsible open={false} title={t('where.title')}><Where barcode={p.id} liquid={isLiquid(p)} /></Collapsible>
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

      <Sheet open={!!sheet} onClose={() => setSheet(null)} title={sheet ? sheet.toUpperCase() + (info ? ' · ' + info.name : sItem?.name ? ' · ' + sItem.name : '') : ''}>
        {info ? <><h3>{t('add.why')}</h3><p>{info.why}</p><h3>{t('add.evidence')}</h3><p>{info.evidence}</p><h3>{t('add.regulation')}</h3><p>{info.regulation}</p><h3>{t('add.advice')}</h3><p>{info.advice}</p>
          <p className="mut sm">{t('add.source')} : <a target="_blank" rel="noreferrer" href={info.source}>EFSA / UE</a></p></>
          : sItem?.known ? <><p><span className={'pill ' + (sItem.level === 'D' ? 'b' : sItem.level === 'C' ? 'w' : 'g')}>{t('addl.' + sItem.level)}</span></p>{sItem.note && <p>{sItem.note}</p>}
            <p className="mut sm"><a target="_blank" rel="noreferrer" href="https://food.ec.europa.eu/food-safety/food-improvement-agents/additives/database_en">{t('add.euDb')}</a></p></>
          : <><p className="mut">{t('add.unknown')}</p><a target="_blank" rel="noreferrer" href="https://food.ec.europa.eu/food-safety/food-improvement-agents/additives/database_en">{t('add.euDb')}</a></>}
        <Button onPress={() => setSheet(null)}>{t('common.done')}</Button>
      </Sheet>
      <InstallCard />
      <DesktopQRBanner />
    </Screen>
  );
}
