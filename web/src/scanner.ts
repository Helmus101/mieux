// Camera + barcode detection (web). Expo replacement: expo-camera <CameraView onBarcodeScanned>.
/* eslint-disable @typescript-eslint/no-explicit-any */

import { validBarcode } from '@shared/barcode';
export { validBarcode };

/** A short tick on a hit. Chrome blocks vibration until the user has tapped the page (and logs a warning), so wait for that. */
const buzz = () => { try { if ((navigator as any).userActivation?.hasBeenActive !== false) navigator.vibrate?.(30); } catch { /* ignore */ } };

export class Cancelled extends Error { constructor() { super('cancelled'); this.name = 'Cancelled'; } }

/** isCurrent lets a caller abandon a start that was superseded (React StrictMode mounts twice; fast navigation) before it touches the video. */
export async function openCamera(video: HTMLVideoElement, isCurrent: () => boolean = () => true): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30 } },
  });
  if (!isCurrent()) { stream.getTracks().forEach((t) => t.stop()); throw new Cancelled(); }
  video.srcObject = stream; video.setAttribute('playsinline', ''); video.muted = true;
  try { await video.play(); } catch (e) {
    if ((e as Error).name === 'AbortError') { if (!isCurrent()) { stream.getTracks().forEach((t) => t.stop()); throw new Cancelled(); } await video.play(); } // interrupted by a reload: retry once
    else throw e;
  }
  if (!isCurrent()) { stream.getTracks().forEach((t) => t.stop()); throw new Cancelled(); }
  // Continuous focus is asked for after the camera is already running: putting it in the first request can slow the start or make it fail.
  try { void stream.getVideoTracks()[0]?.applyConstraints({ advanced: [{ focusMode: 'continuous' } as any] }).catch(() => undefined); } catch { /* not supported */ }
  // A little optical zoom lets the phone stay at a distance where it can focus, and makes thin bars wider in pixels.
  try {
    const tr = stream.getVideoTracks()[0], z = (tr?.getCapabilities?.() as any)?.zoom;
    if (z && typeof z.max === 'number') void tr.applyConstraints({ advanced: [{ zoom: Math.min(z.max, Math.max(z.min ?? 1, 1.6)) } as any] }).catch(() => undefined);
  } catch { /* not supported */ }
  return stream;
}
/** Downloads the barcode decoder ahead of time (browsers without a native detector, e.g. iPhone Safari). */
export const preloadDecoder = () => { if (!('BarcodeDetector' in window)) void import('./zxing'); };
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
/** `continuous`: keeps reading after a hit; the same code is ignored for 3 s so holding the phone still does not repeat it. */
export async function scanBarcodes(video: HTMLVideoElement, onCode: (code: string) => void, frame?: HTMLElement | null, continuous = false): Promise<() => void> {
  let stopped = false, lastCode = '', lastAt = 0;
  const done = (c: string) => {
    if (stopped || !validBarcode(c)) return false;
    if (continuous) { const now = Date.now(); if (c === lastCode && now - lastAt < 3000) return false; lastCode = c; lastAt = now; buzz(); onCode(c); return false; }
    stopped = true; buzz(); onCode(c); return true; };
  // Next video frame: in step with the camera when the browser can say so, else the display refresh.
  const nextFrame = (cb: () => void) => { const v = video as any; if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(() => cb()); else requestAnimationFrame(() => cb()); };
  // Native detector when it reads EAN/UPC; ZXing otherwise. Frames are never queued: one decode at a time, always on the freshest frame.
  let det: any = null;
  if ('BarcodeDetector' in window) {
    try {
      const sup: string[] = await (window as any).BarcodeDetector.getSupportedFormats?.() ?? [];
      const want = ['ean_13', 'ean_8', 'upc_a', 'upc_e'].filter((f) => !sup.length || sup.includes(f));
      if (want.length) det = new (window as any).BarcodeDetector({ formats: want });
    } catch { det = null; }
  }
  const cv = document.createElement('canvas'), cx = cv.getContext('2d', { willReadFrequently: true })!;
  const crop = (maxW: number) => {
    const g = frameRegion(video, frame), k = Math.min(1, maxW / g.sw);
    cv.width = Math.max(1, Math.round(g.sw * k)); cv.height = Math.max(1, Math.round(g.sh * k));
    cx.drawImage(video, g.sx, g.sy, g.sw, g.sh, 0, 0, cv.width, cv.height);
  };
  if (det) {
    const loop = async () => {
      if (stopped) return;
      if (video.readyState >= 2 && video.videoWidth) {
        try {
          crop(1024);  // detail matters more than speed here: the native detector is fast and thin bars blur away when downscaled
          let r = await det.detect(cv);
          if (!r.length) r = await det.detect(video);  // barcode outside the frame: look at the whole picture
          for (const b of r) if (done(b.rawValue)) return;
        } catch { /* keep going */ }
      }
      nextFrame(loop);
    };
    nextFrame(loop);
  } else {
    const Z = await import('./zxing');
    const reader = new Z.MultiFormatUPCEANReader();
    // Also try the picture with its colours inverted (light bars on dark packaging) when the normal read finds nothing.
    const decodeBoth = (rd: any, canvas: HTMLCanvasElement) => { try { return Z.decodeCanvas(rd, canvas); } catch { cx.globalCompositeOperation = 'difference'; cx.fillStyle = '#fff'; cx.fillRect(0, 0, canvas.width, canvas.height); cx.globalCompositeOperation = 'source-over'; return Z.decodeCanvas(rd, canvas); } };
    let seen = '', seenAt = 0;
    let n = 0;
    const loop = () => {
      if (stopped) return;
      if (video.videoWidth) {
        // Alternate views so one of them lands: the scan frame at two resolutions, then the whole picture.
        const view = n++ % 3;
        if (view === 2) { const g = { sx: 0, sy: 0, sw: video.videoWidth, sh: video.videoHeight }, k = Math.min(1, 1280 / g.sw); cv.width = Math.round(g.sw * k); cv.height = Math.round(g.sh * k); cx.drawImage(video, 0, 0, cv.width, cv.height); }
        else crop(view ? 1280 : 800);
        try {
          const c = decodeBoth(reader, cv), now = Date.now();
          // ZXing misreads more often than the native detector: trust a code once two reads in a row agree
          if (validBarcode(c)) { if (c === seen && now - seenAt < 1200) { if (done(c)) return; } else { seen = c; seenAt = now; } }
        } catch { /* no code in this frame */ }
      }
      nextFrame(loop);
    };
    nextFrame(loop);
  }
  return () => { stopped = true; };
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
  const Z = 'BarcodeDetector' in window ? null : await import('./zxing');
  const zx = Z ?? await import('./zxing');
  const reader = new zx.MultiFormatUPCEANReader();
  const det = 'BarcodeDetector' in window ? new (window as any).BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] }) : null;
  // Photos are tried at several sizes: a huge picture or a tiny code each read best at a different scale.
  for (const width of [1600, 1000, 2400, 600]) {
    const cv = document.createElement('canvas'), k = Math.min(1, width / bmp.width);
    cv.width = Math.max(1, Math.round(bmp.width * k)); cv.height = Math.max(1, Math.round(bmp.height * k));
    cv.getContext('2d')!.drawImage(bmp, 0, 0, cv.width, cv.height);
    if (det) { try { for (const b of await det.detect(cv)) if (validBarcode(b.rawValue)) return b.rawValue; } catch { /* fall through */ } }
    try { const c = zx.decodeCanvas(reader, cv); if (validBarcode(c)) return c; } catch { /* next size */ }
  }
  return null;
}
