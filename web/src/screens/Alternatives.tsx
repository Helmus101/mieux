import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory, useProfile } from '@shared/stores';
import { CHAIN_LIST } from '@shared/chains';
import { Button, Card, ChainLogo, Muted, NavBar, NovaBadge, NutriScore, Pill, Row, Screen, Segmented, Sheet, Skeleton, Toast, haptic } from '../ui';
import { formatCents, isLiquid, unitPrice } from '@shared/utils/format';
import { routes, useNav } from '../nav';
import Where from '../Where';
import { friendlyError } from '../errors';

/* eslint-disable @typescript-eslint/no-explicit-any */
const NEAR_KM = 5; // only products sold at a chain with a branch within 5 km of home: fixed, not a setting
const sizeLabel = (q: { amount: number; unit: string }) => (q.amount >= 1000 ? `${Math.round(q.amount / 100) / 10} ${q.unit === 'ml' ? 'L' : 'kg'}`.replace('.', ',') : `${Math.round(q.amount)} ${q.unit}`);

export default function Alternatives() {
  const { barcode } = useParams<{ barcode: string }>();
  const { go, back } = useNav();
  const saved = useProfile((s) => s.priorities), estimates = useProfile((s) => s.estimates);
  const addSearch = useHistory((s) => s.addSearch);
  const home = useProfile((s) => s.place);
  const hasHome = home?.lat != null;
  const myChains = (useProfile((s) => s.chains) ?? []).filter((id) => CHAIN_LIST.some((c) => c.id === id));
  // "Today" filters start from the saved profile and never write back to it.
  // Quality is judged on nutrition only; the price tabs come from the price rankings, so no price priority is sent.
  const prios = (() => { const q = saved.filter((k) => k !== 'budget' && k !== 'value'); return q.length ? q : ['overall']; })();
  const [tries, setTry] = useState(0); const picked = useRef(false); const [detail, setDetail] = useState<any | null>(null); const radius = NEAR_KM, [diffBy, setDiffBy] = useState<'kg' | 'pack'>('kg'), [sameSize, setSameSize] = useState(false), [subMax, setSubMax] = useState(3), [hidden, setHidden] = useState<string[]>([]); const mode = 'similar', pc = 'any'; const [rk, setRk] = useState('value');
  const [r, setR] = useState<any>(null), [busy, setBusy] = useState(true), [err, setErr] = useState<{ title: string; why: string } | null>(null);
  const [expl, setExpl] = useState<Record<string, any>>({}), [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    if (!barcode || !prios.length) return;
    setBusy(true); setErr(null);
    api.getAlternatives(barcode, { priorities: prios, category_mode: mode, limit: 10, substitution_max: subMax, same_size: sameSize, chains: myChains, price_constraint: pc, approximate: estimates, ...(hasHome ? { location: { lat: home!.lat, lon: home!.lon, radius_km: NEAR_KM }, nearby_only: true } : {}) })
      .then((x: any) => { setR(x); if (!picked.current) { const has = (k: string) => x.rankings?.[k === 'match' ? 'quality' : k]?.length > 0; const first = ['value', 'match', 'budget'].find((k) => k && has(k)); if (first) setRk(first); } addSearch({ originalId: barcode, originalName: x.original?.name ?? barcode, priorities: prios, mode, results: x.alternatives.map((a: any) => ({ id: a.product_id, name: a.product.name, brand: a.product.brand, priceCents: a.price_per_100_cents != null ? Math.round(a.price_per_100_cents) : null })) }); })
      .catch((e: unknown) => setErr(friendlyError(e))).finally(() => setBusy(false));
  }, [barcode, prios.join(), mode, pc, estimates, home?.lat, home?.lon, subMax, sameSize, myChains.join(), tries]);
  const explain = async (id: string) => { setExpl((e) => ({ ...e, [id]: { loading: true } })); try { const x = await api.explain(barcode!, id); setExpl((e) => ({ ...e, [id]: x })); } catch { setExpl((e) => ({ ...e, [id]: null })); } };
  const entries = (r?.rankings?.[rk === 'match' ? 'quality' : rk] ?? []).map((e: any) => ({ product: e.product, why: e.why, tradeoffs: e.tradeoffs ?? [], price100: e.price_per_100_cents, estimated: e.estimated, dominated: e.dominated, vs: e.value_score, ps: e.price_score, nearby: e.nearby, priceDate: e.price_date ?? e.price_source?.date, stale: e.price_stale ?? e.price_source?.stale, size: e.size ?? e.product.quantity, pack: e.pack_cents, ratio: e.size_ratio }));
  // An alternative is shown only if it beats the scanned product on at least one thing: a higher quality score, or a lower price per kilo/litre.
  const better = (e: any) => {
    const os = r?.original?.score?.total, ps = r?.original_price?.per100_cents;
    const q = os != null && e.product.score?.total != null && e.product.score.total > os;
    const c = ps != null && e.price100 != null && e.price100 < ps - 0.05;
    const v = e.vs != null;
    return q || c || v || ps == null;  // no price of your own: products with a real price are listed by price, and the note says so
  };
  const shown = entries.filter((e: any) => !hidden.includes(e.product.id) && better(e));
  const nothingNear = hasHome && !!r && ['budget', 'value', 'quality'].every((k) => !(r.rankings?.[k]?.length));  // nothing sold within the radius at all, whatever the tab
  // Only the difference against the scanned product is shown in the list (per kilo/litre, or per pack); real prices are in the details.
  const diffOf = (e: any): { text: string; tone: string; sub?: string } | null => {
    const o = r?.original_price;
    if (!o) return null;
    const liquid = isLiquid(e.product) || r?.original_size?.unit === 'ml';
    const fmt = (c: number) => `${c < 0 ? '−' : '+'}${formatCents(Math.abs(Math.round(c)))}`;
    const tone = (c: number) => (Math.abs(c) < 1 ? 'var(--mut)' : c < 0 ? 'var(--accent)' : 'var(--bad)');
    if (diffBy === 'pack') {
      if (e.pack == null || o.pack_cents == null) return null;
      const c = e.pack - o.pack_cents;
      return { text: Math.abs(c) < 1 ? t('diff.sameShort') : `${fmt(c)} ${t('diff.perPack')}`, tone: tone(c), sub: e.price100 != null ? (() => { const k = (e.price100 - o.per100_cents) * 10; return `${fmt(k)}${liquid ? '/L' : '/kg'}`; })() : undefined };
    }
    if (e.price100 == null) return null;
    const k = (e.price100 - o.per100_cents) * 10, pct = Math.round(((e.price100 - o.per100_cents) / o.per100_cents) * 100);
    return { text: Math.abs(k) < 1 ? t('diff.sameShort') : `${fmt(k)}${liquid ? '/L' : '/kg'}`, tone: tone(k), sub: Math.abs(k) < 1 ? undefined : `${pct > 0 ? '+' : ''}${pct} % ${t('diff.vs')}` };
  };
  const detailBody = (e: any) => (<>
              {e.why && <p style={{ margin: '0 0 8px' }}>{e.why}</p>}
              {(() => { const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product)); return u ? <p className="mut sm" style={{ margin: '0 0 6px' }}>{t('diff.real')} : <b>{t(u.unit === 'L' ? 'simple.perL' : 'simple.perKg', { p: formatCents(u.perUnitCents) })}</b>{e.pack != null ? ` · ${t('size.pack', { s: e.size?.amount ? sizeLabel(e.size) : '' })} ${formatCents(e.pack)}` : ''}</p> : null; })()}
              <Row wrap><NutriScore grade={e.product.nutriScore} /><NovaBadge group={e.product.novaGroup} estimated={e.product.novaEstimated} />{e.estimated && <Pill tone="w">{t('est.pill')}</Pill>}{e.product.frEvidence === 'off_tag' && <Pill tone="g">{t('where.toConfirm')}</Pill>}</Row>
              {(e.vs != null || e.ps != null) && <p className="mut sm">{t('score.value')} {e.vs ?? '—'} · {t('score.priceScore')} {e.ps ?? '—'}</p>}
              {e.tradeoffs?.length > 0 && <p className="mut sm">{t('alt.tradeoffs')} : {e.tradeoffs.slice(0, 2).join(' ; ')}</p>}
              {expl[e.product.id]?.text && <Card tint><p style={{ margin: 0 }}>{expl[e.product.id].text}</p></Card>}
              <Row wrap>
                <Button primary onPress={() => { setDetail(null); go(routes.product(e.product.id)); }}>{t('alt.seeProduct')}</Button>
                {!expl[e.product.id]?.text && <Button small plain onPress={() => explain(e.product.id)}>{expl[e.product.id]?.loading ? t('ex.loading') : t('ex.button')}</Button>}
                <Button small plain onPress={async () => { try { await api.substitutionVerdict(barcode!, e.product.id, 'not_comparable'); haptic('warning'); setHidden((h) => [...h, e.product.id]); setDetail(null); setNote(t('sub.thanks')); setTimeout(() => setNote(null), 2000); } catch { /* offline: keep it */ } }}>{t('sub.notComparable')}</Button>
              </Row>
              <h3 style={{ marginTop: 24 }}>{t('where.title')}</h3><Where barcode={e.product.id} liquid={isLiquid(e.product)} />
              {e.product.chains?.length > 0 && <div className="logos">{e.product.chains.slice(0, 6).map((c: string) => <ChainLogo key={c} id={c} size={22} />)}{e.product.chains.length > 6 && <span className="mut sm">+{e.product.chains.length - 6}</span>}</div>}
  </>);
  return (
    <Screen>
      <NavBar onBack={back} title={t('alt.title')} />
      <h1>{t('alt.title')}</h1>
      {r?.original && <Muted>{r.original.name}</Muted>}
      <Segmented value={rk} onChange={(k) => { picked.current = true; setRk(k); }} options={[{ key: 'budget', label: t('rank.budget') }, { key: 'match', label: t('rank.match') }, { key: 'value', label: t('rank.value') }]} />
      {r?.original_price && <Segmented value={diffBy} onChange={(k) => setDiffBy(k as 'kg' | 'pack')} options={[{ key: 'kg', label: t('diff.byKg') }, { key: 'pack', label: t('diff.byPack') }]} />}
      {r?.original_price?.per100_cents != null && <p className="sm" style={{ margin: '2px 0 8px' }}>{t('diff.yours')} : <b>{formatCents(Math.round(r.original_price.per100_cents * 10))}{isLiquid(r.original) || r?.original_size?.unit === 'ml' ? '/L' : '/kg'}</b>{r.original_size?.amount ? ` · ${sizeLabel(r.original_size)}` : ''}{r.original_price.pack_cents != null ? ` · ${formatCents(r.original_price.pack_cents)}` : ''}</p>}
      {busy && <><Skeleton h={150} /><Skeleton h={150} /></>}
      {err && <Card><b>{err.title}</b><Muted>{err.why}</Muted><Button small onPress={() => setTry((n) => n + 1)}>{t('errs.retry')}</Button></Card>}
      {r && !busy && !shown.length && (() => {
        const os = r?.original?.score?.total;
        const m = nothingNear ? { title: t('emptyAlt.nearTitle'), why: t('emptyAlt.nearWhy', { r: radius }), action: <Button small onPress={() => go(routes.profile)}>{t('emptyAlt.nearAction')}</Button> }
          : sameSize ? { title: t('emptyAlt.sameTitle'), why: t('emptyAlt.sameWhy'), action: <Button small onPress={() => setSameSize(false)}>{t('emptyAlt.sameAction')}</Button> }
          : rk === 'match' ? { title: t('emptyAlt.qualityTitle'), why: os != null ? t('emptyAlt.qualityWhy', { s: os }) : t('emptyAlt.qualityWhyNoScore') }
          : r?.rankings?.no_baseline ? { title: t('emptyAlt.noPriceTitle'), why: t('emptyAlt.noPriceWhy') }
          : rk === 'budget' ? { title: t('emptyAlt.cheaperTitle'), why: t('emptyAlt.cheaperWhy') }
          : { title: t('emptyAlt.valueTitle'), why: t('emptyAlt.valueWhy') };
        return <Card><b>{m.title}</b><p className="mut" style={{ margin: '10px 0 0' }}>{m.why}</p>{m.action && <div style={{ marginTop: 14 }}>{m.action}</div>}</Card>;
      })()}
      {r && !busy && shown.map((e: any, i: number) => {
        return (
          <Card key={e.product.id}>
            <Row>{e.product.imageUrl && <img src={e.product.imageUrl} alt="" width={56} height={56} style={{ objectFit: 'contain', borderRadius: 12, background: '#fff' }} />}
              <div className="grow"><b>{i + 1}. {e.product.name}</b><Muted>{e.product.brand}</Muted></div></Row>
            <Row spread>
              {e.product.score ? <span><b style={{ fontSize: 28, letterSpacing: -.5 }}>{e.product.score.total}</b><span className="mut sm">{t('score.outOf')} · {t('score.' + e.product.score.band)}</span>
                {r?.original?.score && (() => { const d = e.product.score.total - r.original.score.total; return <span className="sm" style={{ marginLeft: 8, fontWeight: 600, color: d > 0 ? 'var(--accent)' : d < 0 ? 'var(--bad)' : 'var(--mut)' }}>{d === 0 ? t('score.same') : `${d > 0 ? '+' : '−'}${Math.abs(d)} ${t('score.pts')}`}</span>; })()}</span> : <span />}
              {(() => {
                const d = diffOf(e);
                if (d) return <b style={{ fontSize: 20, color: d.tone }}>{d.text}</b>;
                const u = unitPrice(e.price100, e.product.quantity, isLiquid(e.product));
                return u ? <b style={{ fontSize: 20 }}>{t(u.unit === 'L' ? 'simple.perL' : 'simple.perKg', { p: formatCents(u.perUnitCents) })}</b> : <span className="mut sm">{t('diff.unknown')}</span>;
              })()}
            </Row>
            {e.product.chains?.length > 0 && <div className="logos" style={{ marginTop: 8 }}>{e.product.chains.slice(0, 6).map((c: string) => <ChainLogo key={c} id={c} size={22} />)}{e.product.chains.length > 6 && <span className="mut sm">+{e.product.chains.length - 6}</span>}</div>}
            <Button small plain onPress={() => { haptic('tap'); setDetail(e); }}>{t('simple.moreInfo')}</Button>
          </Card>);
      })}
      {r && !busy && <Row wrap><Button small plain onPress={() => setSameSize(!sameSize)}>{sameSize ? t('size.all') : t('size.same')}</Button>{sameSize && r && !r.same_size_applied && <span className="mut sm">{t('size.unknown')}</span>}</Row>}
      {r && !busy && <Button small plain onPress={() => setSubMax(subMax === 3 ? 4 : 3)}>{subMax === 3 ? t('sub.widen') : t('sub.narrow')}</Button>}
      <Sheet open={!!detail} onClose={() => setDetail(null)} title={detail?.product.name}>{detail && detailBody(detail)}</Sheet>
      <Toast text={note} />
    </Screen>
  );
}
