import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { useSpringDrag } from './spring';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { useHistory } from '@shared/stores';
import { countScan } from './account';
import { Loader, Skeleton } from './ui';
import { prodKey, writeCache } from './swr';
import { getStrict } from '@shared/config';

/* eslint-disable @typescript-eslint/no-explicit-any */
const ProductPage = lazy(() => import('./screens/Product'));

/** A quick card over the live camera: title, the two scores and a way into the full page. It stays until the shopper closes it or scans another product. */
export default function ScanPeek({ code, onExpandedChange, onClose }: { code: string; onExpandedChange?: (open: boolean) => void; onClose: () => void }) {
  const [d, setD] = useState<any>(null), [failed, setFailed] = useState(false), lastDrag = useRef(0);
  // The card grows into the full product page without leaving the scanner: tap it or swipe it up; scroll down to read; pull down from the top to shrink it again.
  const [expanded, setExpanded] = useState(false), [shown, setShown] = useState(false);
  const body = useRef<HTMLDivElement>(null), touch = useRef({ y: 0, top: 0 });
  const expand = () => { setExpanded(true); onExpandedChange?.(true); requestAnimationFrame(() => requestAnimationFrame(() => setShown(true))); };
  const collapse = () => { setShown(false); onExpandedChange?.(false); setTimeout(() => setExpanded(false), 360); };
  useEffect(() => () => onExpandedChange?.(false), []);   // closing the card or scanning another product unlocks the scanner
  // The card waits for the price lookup (started the moment the product is known) before it can be opened:
  // "Recherche du prix…" shows while it runs, then the page opens with the price already cached.
  const [priceDone, setPriceDone] = useState(false);
  const PRICE_WAIT_MS = 12000;   // same ceiling as the product page: after this the card opens anyway
  const addScan = useHistory((s) => s.addScan);
  // Dragged down it follows the finger, and a flick throws it off screen (momentum-projected); a short pull springs back.
  const { ref, set } = useSpringDrag<HTMLDivElement>({
    axis: 'y', response: 0.3, bounce: 0.1, snaps: () => [0, 220],
    onMove: (y) => { if (y) lastDrag.current = performance.now(); if (ref.current) ref.current.style.opacity = String(1 - Math.min(1, Math.max(0, y) / 160)); },
    onSettle: (pt) => { if (pt > 0) onClose(); },
  });
  useEffect(() => {
    let live = true; setD(null); setFailed(false); set(0); setPriceDone(false);
    // Both requests start together: the price endpoint loads the product itself, so there is nothing to wait for.
    // PRICE_WAIT_MS bounds the whole wait from the scan, not from the product fetch.
    const giveUp = setTimeout(() => { if (live) setPriceDone(true); }, PRICE_WAIT_MS);
    api.getWebPriceQuick(code).then(() => undefined).catch(() => undefined).finally(() => { if (live) { clearTimeout(giveUp); setPriceDone(true); } });
    api.getProduct(code).then((x: any) => {
      if (!live) return; setD(x); writeCache(prodKey(code, false, getStrict()), x); addScan(x.product); api.addScan(code).catch(() => undefined); countScan(code);
    })
      .catch(() => { if (live) { setFailed(true); setPriceDone(true); } });
    return () => { live = false; clearTimeout(giveUp); };
  }, [code]);
  const p = d?.product, sc = p?.score;
  const conflict = (d?.fit ?? []).some((x: any) => (x.priority.startsWith('allergen:') || x.priority.startsWith('diet:')) && x.status === 'conflict');
  const tone = conflict ? 'b' : sc?.tone;
  const color = tone === 'b' ? 'var(--bad)' : tone === 'w' ? 'var(--warn)' : 'var(--accent)';
  const pq: number | null = d?.price_context?.value?.value_score ?? null;
  const verdict = conflict ? t('scan.peekConflict') : sc ? t('score.' + sc.band) : t('score.na');
  return (
    <>
    <div ref={ref} className={'peek' + (expanded ? ' peek-hidden' : '')} role="button" tabIndex={0} aria-label={t('scan.peekOpen')} style={{ cursor: priceDone ? undefined : 'wait' }}
      onTouchStart={(e) => { touch.current.y = e.touches[0].clientY; }} onTouchEnd={(e) => { if (p && touch.current.y - e.changedTouches[0].clientY > 36) expand(); }}
      onClick={() => { if (p && performance.now() - lastDrag.current > 200) expand(); }} onKeyDown={(e) => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ') && p) { e.preventDefault(); expand(); } }}>
      <button className="peek-x" aria-label={t('scan.close')} onClick={(e) => { e.stopPropagation(); onClose(); }}>×</button>
      {failed ? <span className="mut">{t('scan.peekFailed')}</span> : !p ? <><Skeleton h={18} w="60%" /><Skeleton h={14} w="35%" /></> : <>
        <div className="peek-top">
          {p.imageUrl && <img src={p.imageUrl} alt="" />}
          <div className="peek-main"><b>{p.name}</b>{p.brand && p.brand.toLowerCase() !== (p.name ?? '').toLowerCase() && <span className="mut sm">{p.brand}</span>}</div>
        </div>
        <div className="peek-scores">
          <div><span className="peek-cap">{t('score.quality')}</span><div className="peek-n" style={{ color }}>{sc ? sc.total : '–'}<i>/100</i></div><small>{verdict}</small></div>
          <div><span className="peek-cap">{t('score.value')}</span><div className="peek-n" style={{ color: pq == null ? 'var(--mut)' : pq >= 65 ? 'var(--accent)' : pq >= 40 ? 'var(--warn)' : 'var(--bad)' }}>{pq ?? '–'}<i>/100</i></div><small>{t('score.pq')}</small></div>
        </div>
        <button className="peek-open" onClick={(e) => { e.stopPropagation(); expand(); }}>{t('scan.peekView')}</button>
        <span className="peek-grip" aria-hidden />
      </>}
    </div>
      {expanded && (
        <div className={'peek-sheet' + (shown ? ' open' : '')} onClick={(e) => e.stopPropagation()}
          onTouchStart={(e) => { touch.current = { y: e.touches[0].clientY, top: body.current?.scrollTop ?? 0 }; }}
          onTouchEnd={(e) => { if (touch.current.top <= 0 && e.changedTouches[0].clientY - touch.current.y > 80) collapse(); }}>
          <div className="peek-handle" onClick={collapse} role="button" aria-label={t('common.back')}><i /></div>
          <div className="peek-body" ref={body}>
            <Suspense fallback={<Loader />}><ProductPage barcode={code} onBack={collapse} /></Suspense>
          </div>
        </div>
      )}
    </>
  );
}
