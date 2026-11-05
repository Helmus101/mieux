import { useEffect, useState } from 'react';
import { api, type PhotoIdentification, type PhotoMatch } from '@shared/api/client';
import { t } from '@shared/i18n';
import { haptic } from './ui';

/** Phone photos are several MB: a 1280 px JPEG is plenty to read a label and keeps the upload fast. */
async function shrink(file: File, max = 1280): Promise<string> {
  const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' }).catch(() => createImageBitmap(file));
  const k = Math.min(1, max / Math.max(bmp.width, bmp.height));
  const c = document.createElement('canvas');
  c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
  c.getContext('2d')!.drawImage(bmp, 0, 0, c.width, c.height);
  bmp.close?.();
  return c.toDataURL('image/jpeg', 0.82).split(',')[1];
}

/** Beta: a photo of any pack -> brand and name read by an AI -> candidate products with their barcodes from the database. */
export default function PhotoIdentify({ file, onPick, onClose }: { file: File; onPick: (barcode: string) => void; onClose: () => void }) {
  const [res, setRes] = useState<PhotoIdentification | null>(null), [err, setErr] = useState('');
  useEffect(() => {
    let live = true;
    shrink(file).then((b64) => api.identifyPhoto(b64)).then((r) => { if (live) { setRes(r); haptic(r.matches.length ? 'success' : 'error'); } })
      .catch((e) => { if (!live) return; haptic('error'); const s = e?.response?.status; setErr(t(s === 503 ? 'beta.unavailable' : s === 429 ? 'beta.slow' : 'beta.fail')); });
    return () => { live = false; };
  }, [file]);
  const pick = (m: PhotoMatch) => { haptic('success'); api.getProduct(m.barcode).catch(() => undefined); onPick(m.barcode); };
  const said = res ? [res.brand, res.name, res.variant, res.size].filter(Boolean).join(' · ') : '';
  return (
    <div className="ph-sheet" role="dialog" aria-modal="true">
      <div className="ph-card">
        {!res && !err && <><h2>{t('beta.reading')}</h2><p className="mut">{t('beta.readingSub')}</p><div className="ph-spin" aria-hidden /></>}
        {err && <p>{err}</p>}
        {res && !res.identified && !res.matches.length && <p>{t('beta.notProduct')}</p>}
        {res && (res.identified || res.matches.length > 0) && <>
          {said && <p className="mut sm" style={{ margin: 0 }}>{t('beta.saw', { x: said })}</p>}
          {res.confidence === 'low' && <p className="mut sm" style={{ margin: '4px 0 0' }}>{t('beta.low')}</p>}
          {res.matches.length > 0 ? <>
            <h2>{t('beta.pick')}</h2>
            <div className="ph-list">
              {res.matches.map((m) => (
                <button key={m.barcode} className="ph-item" onClick={() => pick(m)}>
                  {m.image ? <img src={m.image} alt="" width={44} height={44} loading="lazy" /> : <span className="ph-noimg" />}
                  <span><b>{m.name}</b><br /><span className="mut sm">{[m.brand, m.quantity].filter(Boolean).join(' · ')}{m.exact ? ' · ' + t('beta.exact') : ''}</span></span>
                </button>
              ))}
            </div>
          </> : <p>{t('beta.noMatch')}</p>}
        </>}
        <button className="ph-close" onClick={() => { haptic('tap'); onClose(); }}>{t('beta.retry')}</button>
      </div>
    </div>
  );
}
