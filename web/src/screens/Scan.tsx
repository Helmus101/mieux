import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '@shared/api/client';
import { useProfile } from '@shared/stores';
import { t } from '@shared/i18n';
import { haptic } from '../ui';
import { scanClick } from '../haptics';
import { routes, useNav } from '../nav';
import { InstallCard } from '../InstallPrompt';
import { Cancelled, closeCamera, decodeImage, openCamera, preloadDecoder, scanBarcodes, setTorch, torchSupported } from '../scanner';

// Products are identified by their barcode only: from the live camera or from a photo of the barcode. No typed codes, no name search.
export default function Scan() {
  const { go } = useNav();
  const forCompare = !!(useLocation().state as { compare?: boolean } | null)?.compare;  // opened from Compare: add the scanned product there instead of opening it
  const addCompare = useProfile((st) => st.addCompare);
  const open = (c: string) => { if (forCompare) { addCompare(c); go(routes.compare); } else go(routes.product(c)); };
  const video = useRef<HTMLVideoElement>(null), frame = useRef<HTMLDivElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const stopScan = useRef<(() => void) | null>(null);
  const run = useRef(0);
  const [on, setOn] = useState(false), [torch, setTorchOn] = useState(false), [canTorch, setCanTorch] = useState(false), [err, setErr] = useState('');

  const stop = () => { run.current++; stopScan.current?.(); stopScan.current = null; closeCamera(stream.current); stream.current = null; setOn(false); };
  const start = async () => {
    setErr('');
    const id = ++run.current;
    preloadDecoder();  // downloads while the camera starts, not after
    try {
      stream.current = await openCamera(video.current!, () => id === run.current); setOn(true); setCanTorch(torchSupported(stream.current));
      const stopper = await scanBarcodes(video.current!, (c) => { scanClick(); haptic('success'); api.getProduct(c).catch(() => undefined); stop(); open(c); }, frame.current);
      if (id !== run.current) { stopper(); return; }
      stopScan.current = stopper;
    } catch (e) { if (!(e instanceof Cancelled)) haptic('error'); if (!(e instanceof Cancelled)) setErr(t((e as Error).name === 'NotAllowedError' ? 'scan.camDenied' : (e as Error).name === 'NotFoundError' ? 'scan.camNone' : 'scan.camFail', { e: (e as Error).message })); }
  };
  useEffect(() => { start(); return stop; }, []); // the live camera opens as soon as the screen does
  const flip = async () => { haptic('tap'); setTorchOn(await setTorch(stream.current, !torch)); };
  const fromPhoto = async (f?: File) => {
    if (!f) return; setErr('');
    const c = await decodeImage(f).catch(() => null);
    if (c) { scanClick(); haptic('success'); stop(); open(c); } else { haptic('error'); setErr(t('scan.noCode')); }
  };
  const close = () => { haptic('tap'); stop(); go(forCompare ? routes.compare : routes.home); };
  return (
    <div className="cam">
      <video ref={video} muted playsInline />
      <div className="cam-mask"><div className="cam-frame" ref={frame}><i /></div></div>
      <div className="cam-top">
        <button className="cam-btn" onClick={close} aria-label={t('common.back')}><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
        {canTorch && on && <button className={'cam-btn' + (torch ? ' lit' : '')} onClick={flip} aria-label={t('scan.torch')}><svg viewBox="0 0 24 24"><path d="M7 3h10l-2 7v3l-3 3-3-3v-3zM12 16v5" /></svg></button>}
      </div>
      <div className="cam-bottom">
        {err ? <p className="cam-err">{err}</p> : <p>{on ? (forCompare ? t('compare.scanForCompare') : t('scan.point')) : t('simple.camNeeded')}</p>}
        {!on && <button className="cam-main" onClick={start}>{t('scan.open')}</button>}
        <InstallCard />
        <label className="cam-link">{t('scan.gallery')}<input type="file" accept="image/*" hidden onChange={(e) => fromPhoto(e.target.files?.[0])} /></label>
      </div>
    </div>
  );
}
