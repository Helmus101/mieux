// Camera + barcode detection (web). Expo replacement: expo-camera <CameraView onBarcodeScanned>.
/* eslint-disable @typescript-eslint/no-explicit-any */

import { validBarcode } from '@shared/barcode';
export { validBarcode };

export class Cancelled extends Error { constructor() { super('cancelled'); this.name = 'Cancelled'; } }

/** isCurrent lets a caller abandon a start that was superseded (React StrictMode mounts twice; fast navigation) before it touches the video. */
export async function openCamera(video: HTMLVideoElement, isCurrent: () => boolean = () => true): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 }, advanced: [{ focusMode: 'continuous' } as any] },
  });
  if (!isCurrent()) { stream.getTracks().forEach((t) => t.stop()); throw new Cancelled(); }
  video.srcObject = stream; video.setAttribute('playsinline', ''); video.muted = true;
  try { await video.play(); } catch (e) {
    if ((e as Error).name === 'AbortError') { if (!isCurrent()) { stream.getTracks().forEach((t) => t.stop()); throw new Cancelled(); } await video.play(); } // interrupted by a reload: retry once
    else throw e;
  }
  if (!isCurrent()) { stream.getTracks().forEach((t) => t.stop()); throw new Cancelled(); }
  return stream;
}
export const closeCamera = (s: MediaStream | null) => s?.getTracks().forEach((t) => t.stop());

/** The part of the video frame (in video pixels) that lies under the on-screen scan frame, given object-fit: cover. */
function frameRegion(video: HTMLVideoElement, frame?: HTMLElement | null) {
  const vw = video.videoWidth, vh = video.videoHeight;
  if (!frame || !vw) return { sx: 0, sy: 0, sw: vw, sh: vh };
  const v = video.getBoundingClientRect(), f = frame.getBoundingClientRect();
  const k = Math.max(v.width / vw, v.height / vh), ox = (vw * k - v.width) / 2, oy = (vh * k - v.height) / 2;
  const sx = Math.max(0, (f.left - v.left + ox) / k), sy = Math.max(0, (f.top - v.top + oy) / k);
  return { sx, sy, sw: Math.min(vw - sx, f.width / k), sh: Math.min(vh - sy, f.height / k) };
}

/** Starts scanning an already-playing video. Returns a stop function. Uses the native detector when present (fast), else ZXing on a small centre crop. */
export async function scanBarcodes(video: HTMLVideoElement, onCode: (code: string) => void, frame?: HTMLElement | null): Promise<() => void> {
  let stopped = false, last = 0;
  const done = (c: string) => { if (stopped || !validBarcode(c)) return false; stopped = true; try { navigator.vibrate?.(30); } catch { /* ignore */ } onCode(c); return true; };
  if ('BarcodeDetector' in window) {
    const det = new (window as any).BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
    const cv0 = document.createElement('canvas'), cx0 = cv0.getContext('2d', { willReadFrequently: true })!;
    const loop = async (t: number) => {
      if (stopped) return;
      if (t - last > 60 && video.readyState >= 2) { last = t; try { const g = frameRegion(video, frame); cv0.width = Math.round(g.sw); cv0.height = Math.round(g.sh); cx0.drawImage(video, g.sx, g.sy, g.sw, g.sh, 0, 0, cv0.width, cv0.height); const r = await det.detect(cv0); for (const b of r) if (done(b.rawValue)) return; } catch { /* keep going */ } }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  } else {
    const Z = await import('./zxing');
    const reader = new Z.MultiFormatUPCEANReader();
    const cv = document.createElement('canvas'), cx = cv.getContext('2d', { willReadFrequently: true })!;
    const loop = (t: number) => {
      if (stopped) return;
      if (t - last > 70 && video.videoWidth) {
        last = t;
        // decode only the centre band, downscaled: ~5x faster than the full frame and where the user aims anyway
        const { sx, sy, sw, sh } = frameRegion(video, frame);
        const k = Math.min(1, 720 / sw); cv.width = Math.round(sw * k); cv.height = Math.round(sh * k);
        cx.drawImage(video, sx, sy, sw, sh, 0, 0, cv.width, cv.height);
        try { if (done(Z.decodeCanvas(reader, cv))) return; } catch { /* no code in this frame */ }
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
  return () => { stopped = true; };
}

/** Grabs a full-resolution, contrast-boosted frame for OCR. */
export function captureFrame(video: HTMLVideoElement): Promise<Blob> {
  const cv = document.createElement('canvas'); cv.width = video.videoWidth; cv.height = video.videoHeight;
  const cx = cv.getContext('2d')!; cx.filter = 'grayscale(1) contrast(1.4)'; cx.drawImage(video, 0, 0);
  return new Promise((ok, no) => cv.toBlob((b) => (b ? ok(b) : no(new Error('capture'))), 'image/jpeg', 0.92));
}

/** Torch (flash) toggle where the camera supports it; resolves to whether it is now on. */
export async function setTorch(stream: MediaStream | null, on: boolean): Promise<boolean> {
  const track = stream?.getVideoTracks()[0];
  if (!track) return false;
  try { await track.applyConstraints({ advanced: [{ torch: on } as any] }); return on; } catch { return false; }
}
export const torchSupported = (stream: MediaStream | null) => !!(stream?.getVideoTracks()[0]?.getCapabilities?.() as any)?.torch;

/** Decode a barcode from a photo (gallery). Returns the code or null. */
export async function decodeImage(file: Blob): Promise<string | null> {
  const bmp = await createImageBitmap(file);
  const cv = document.createElement('canvas'); const k = Math.min(1, 1600 / bmp.width);
  cv.width = Math.round(bmp.width * k); cv.height = Math.round(bmp.height * k);
  cv.getContext('2d')!.drawImage(bmp, 0, 0, cv.width, cv.height);
  if ('BarcodeDetector' in window) {
    try { const r = await new (window as any).BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] }).detect(cv); for (const b of r) if (validBarcode(b.rawValue)) return b.rawValue; } catch { /* fall through */ }
  }
  const Z = await import('./zxing');
  const reader = new Z.MultiFormatUPCEANReader();
  try { const c = Z.decodeCanvas(reader, cv); return validBarcode(c) ? c : null; } catch { return null; }
}
