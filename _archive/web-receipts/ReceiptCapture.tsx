import { useEffect, useRef, useState } from 'react';
import { api } from '@shared/api/client';
import { t } from '@shared/i18n';
import { Screen, NavBar, LargeTitle, Card, Button, Muted, Skeleton } from '../ui';
import { routes, useNav } from '../nav';
import { Cancelled, captureFrame, closeCamera, openCamera } from '../scanner';

export default function ReceiptCapture() {
  const { go, back } = useNav();
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const run = useRef(0);
  const [on, setOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [txt, setTxt] = useState('');
  const [err, setErr] = useState('');

  const stop = () => { run.current++; closeCamera(stream.current); stream.current = null; setOn(false); };
  const start = async () => {
    setErr(''); const id = ++run.current;
    try { stream.current = await openCamera(video.current!, () => id === run.current); setOn(true); }
    catch (e) { if (!(e instanceof Cancelled)) setErr(t('scan.camFail', { e: (e as Error).message })); }
  };
  useEffect(() => { start(); return stop; }, []); // the receipt screen opens the camera straight away

  const parse = async (text: string) => {
    const lines = text.split('\n').map((l, i) => ({ text: l.trim(), confidence: 0.9, position: i })).filter((l) => l.text);
    go(routes.receiptReview, { parsed: await api.previewReceipt(lines) });
  };
  const recognise = async (img: Blob | File) => {
    setBusy(true); setErr('');
    try {
      const { default: Tesseract } = await import('tesseract.js'); // on demand; the image never leaves the device
      const r = await Tesseract.recognize(img, 'fra');
      stop(); await parse(r.data.text);
    } catch (e) { setErr(t('receipt.fail') + ' : ' + (e as Error).message); } finally { setBusy(false); }
  };
  const shoot = async () => { if (video.current) await recognise(await captureFrame(video.current)); };
  return (
    <Screen>
      <NavBar onBack={back} title={t('receipt.captureTitle')} />
      <LargeTitle sub={t('receipt.captureText')}>{t('receipt.captureTitle')}</LargeTitle>
      <Card>
        <div style={{ display: on ? 'block' : 'none' }}><video ref={video} muted playsInline style={{ maxHeight: 460 }} /><Muted>{t('receipt.aim')}</Muted></div>
        {!on && <Button primary onPress={start}>{t('scan.open')}</Button>}
        {on && <Button primary disabled={busy} onPress={shoot}>{busy ? t('receipt.reading') : t('receipt.take')}</Button>}
        {busy && <Skeleton h={10} />}
        {err && <p style={{ color: 'var(--bad)' }}>{err}</p>}
        <label className="btn plain" style={{ cursor: 'pointer' }}>{t('receipt.import')}<input type="file" accept="image/*" hidden onChange={(e) => e.target.files?.[0] && recognise(e.target.files[0])} /></label>
      </Card>
      <Card>
        <b>{t('receipt.or')}</b>
        <textarea rows={5} value={txt} onChange={(e) => setTxt(e.target.value)} placeholder={'MONOPRIX\n28/10/2026\nYAOURT GREC 1,59\nTOTAL 1,59'} style={{ marginTop: 8 }} />
        <Button onPress={() => txt.trim() && parse(txt).catch((e) => setErr(e.message))}>{t('receipt.parse')}</Button>
      </Card>
    </Screen>
  );
}
