import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '@shared/api/client';
import { useProfile } from '@shared/stores';
import { t } from '@shared/i18n';
import { Screen, NavBar, LargeTitle, Card, Button, Row, Muted, haptic } from '../ui';
import { routes, useNav } from '../nav';
import { Cancelled, closeCamera, decodeImage, openCamera, scanBarcodes, setTorch, torchSupported } from '../scanner';

// Products are identified by their barcode only: from the live camera or from a photo of the barcode. No typed codes, no name search.
export default function Scan() {
  const { go } = useNav();
  const forCompare = !!(useLocation().state as { compare?: boolean } | null)?.compare;  // opened from Compare: add the scanned product there instead of opening it
  const addCompare = useProfile((st) => st.addCompare);
  const open = (c: string) => { if (forCompare) { addCompare(c); go(routes.compare); } else go(routes.product(c)); };
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const stopScan = useRef<(() => void) | null>(null);
  const run = useRef(0);
  const [on, setOn] = useState(false), [torch, setTorchOn] = useState(false), [canTorch, setCanTorch] = useState(false), [err, setErr] = useState('');

  const stop = () => { run.current++; stopScan.current?.(); stopScan.current = null; closeCamera(stream.current); stream.current = null; setOn(false); };
  const start = async () => {
    setErr('');
    const id = ++run.current;
    try {
      stream.current = await openCamera(video.current!, () => id === run.current); setOn(true); setCanTorch(torchSupported(stream.current));
      const stopper = await scanBarcodes(video.current!, (c) => { haptic('success'); api.getProduct(c).catch(() => undefined); stop(); open(c); });
      if (id !== run.current) { stopper(); return; }
      stopScan.current = stopper;
    } catch (e) { if (!(e instanceof Cancelled)) haptic('error'); if (!(e instanceof Cancelled)) setErr(t('scan.camFail', { e: (e as Error).message })); }
  };
  useEffect(() => { start(); return stop; }, []); // the live camera opens as soon as the screen does
  const flip = async () => { haptic('tap'); setTorchOn(await setTorch(stream.current, !torch)); };
  const fromPhoto = async (f?: File) => {
    if (!f) return; setErr('');
    const c = await decodeImage(f).catch(() => null);
    if (c) { haptic('success'); stop(); open(c); } else { haptic('error'); setErr(t('scan.noCode')); }
  };
  return (
    <Screen>
      <NavBar title={t('scan.title')} />
      <LargeTitle sub={forCompare ? t('compare.scanForCompare') : t('simple.scanSub')}>{t('scan.title')}</LargeTitle>
      <Card>
        <div className="viewfinder" style={{ display: on ? 'block' : 'none' }}><video ref={video} muted playsInline /><i /></div>
        {!on && <div style={{ textAlign: 'center', padding: '28px 0' }}>
          <svg viewBox="0 0 24 24" width="64" height="64" style={{ stroke: 'var(--mut)', fill: 'none', strokeWidth: 1.4, strokeLinecap: 'round' }}><path d="M4 8V5a1 1 0 011-1h3M16 4h3a1 1 0 011 1v3M20 16v3a1 1 0 01-1 1h-3M8 20H5a1 1 0 01-1-1v-3M7 12h10" /></svg>
          <Muted>{t('simple.camNeeded')}</Muted></div>}
        {on ? <Muted>{t('scan.point')}</Muted> : <Button primary onPress={start}>{t('scan.open')}</Button>}
        <Row>{canTorch && on && <Button small onPress={flip}>{t('scan.torch')}{torch ? ' · on' : ''}</Button>}
          <label className="btn sm" style={{ cursor: 'pointer' }}>{t('scan.gallery')}<input type="file" accept="image/*" hidden onChange={(e) => fromPhoto(e.target.files?.[0])} /></label></Row>
        {err && <p style={{ color: 'var(--bad)' }}>{err}</p>}
        <p className="mut sm">{t('scan.hint')}</p>
      </Card>
    </Screen>
  );
}
