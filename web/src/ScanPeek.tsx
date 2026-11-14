import { useEffect, useRef, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { countScan } from './account';
import { Skeleton } from './ui';

/* eslint-disable @typescript-eslint/no-explicit-any */
/** A quick card over the live camera: title, the two scores and a way into the full page. It stays until the shopper closes it or scans another product. */
export default function ScanPeek({ code, onOpen, onClose }: { code: string; onOpen: (code: string) => void; onClose: () => void }) {
  const [d, setD] = useState<any>(null), [failed, setFailed] = useState(false), [dy, setDy] = useState(0), start = useRef<number | null>(null);
  // The card waits for the price lookup (started the moment the product is known) before it can be opened:
  // "Recherche du prix…" shows while it runs, then the page opens with the price already cached.
  const [priceDone, setPriceDone] = useState(false);
  const PRICE_WAIT_MS = 12000;   // same ceiling as the product page: after this the card opens anyway
  const addScan = useHistory((s) => s.addScan);
  useEffect(() => {
    let live = true; setD(null); setFailed(false); setDy(0); setPriceDone(false);
    let giveUp: ReturnType<typeof setTimeout> | undefined;
    api.getProduct(code).then((x: any) => {
      if (!live) return; setD(x); addScan(x.product); api.addScan(code).catch(() => undefined); countScan(code);
      giveUp = setTimeout(() => { if (live) setPriceDone(true); }, PRICE_WAIT_MS);
      api.getWebPriceQuick(code).then(() => undefined).catch(() => undefined).finally(() => { if (live) { if (giveUp) clearTimeout(giveUp); setPriceDone(true); } });
    })
      .catch(() => { if (live) { setFailed(true); setPriceDone(true); } });
    return () => { live = false; if (giveUp) clearTimeout(giveUp); };
  }, [code]);
  const p = d?.product, sc = p?.score;
  const conflict = (d?.fit ?? []).some((x: any) => (x.priority.startsWith('allergen:') || x.priority.startsWith('diet:')) && x.status === 'conflict');
  const tone = conflict ? 'b' : sc?.tone;
  const color = tone === 'b' ? 'var(--bad)' : tone === 'w' ? 'var(--warn)' : 'var(--accent)';
  const pq: number | null = d?.price_context?.value?.value_score ?? null;
  const verdict = conflict ? t('scan.peekConflict') : sc ? t('score.' + sc.band) : t('score.na');
  return (
    <div className="peek" role="button" tabIndex={0} aria-label={t('scan.peekOpen')} style={{ transform: `translateY(${Math.max(0, dy)}px)`, opacity: 1 - Math.min(1, Math.max(0, dy) / 160), transition: start.current == null ? 'transform .2s, opacity .2s' : 'none', cursor: priceDone ? undefined : 'wait' }}
      onClick={() => { if (p && priceDone) onOpen(code); }} onKeyDown={(e) => { if (e.key === 'Enter' && p && priceDone) onOpen(code); }}
      onPointerDown={(e) => { start.current = e.clientY; }} onPointerMove={(e) => { if (start.current != null) setDy(e.clientY - start.current); }}
      onPointerUp={() => { const far = dy > 60; start.current = null; if (far) onClose(); else setDy(0); }} onPointerCancel={() => { start.current = null; setDy(0); }}>
      <button className="peek-x" aria-label={t('scan.close')} onClick={(e) => { e.stopPropagation(); onClose(); }}>×</button>
      {failed ? <span className="mut">{t('scan.peekFailed')}</span> : !p ? <><Skeleton h={18} w="60%" /><Skeleton h={14} w="35%" /></> : <>
        {p.imageUrl && <img src={p.imageUrl} alt="" />}
        <div className="peek-main">
          <b>{p.name}</b>
          <span className="mut sm">{p.brand ?? ''}</span>
          {!priceDone && <span className="mut sm"><span className="mini-ring" /> {t('alt.pricing')}</span>}
          <button className="peek-open" disabled={!priceDone} onClick={(e) => { e.stopPropagation(); if (priceDone) onOpen(code); }}>{t('scan.peekView')}</button>
        </div>
        <div className="peek-score" style={{ color }}>{sc ? sc.total : '–'}<small>{verdict}</small></div>
        <div className="peek-score" style={{ color: pq == null ? 'var(--mut)' : pq >= 65 ? 'var(--accent)' : pq >= 40 ? 'var(--warn)' : 'var(--bad)' }}>{pq ?? '–'}<small>{t('score.pq')}</small></div>
      </>}
    </div>
  );
}
