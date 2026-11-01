// Haptic feedback. Android / Chrome: the Vibration API. iOS Safari has no Vibration API, but toggling a hidden <input type="checkbox" switch>
// gives a native tick (iOS 17.4+) when it runs inside a user gesture, so taps work there while a feedback fired later (for example when the camera
// finds a barcode) can only vibrate on Android. Can be switched off in the profile.
export type HapticKind = 'tap' | 'select' | 'success' | 'warning' | 'error';
const PATTERNS: Record<HapticKind, number | number[]> = { tap: 8, select: 6, success: [12, 50, 18], warning: [20, 40, 20], error: [40, 60, 40, 60, 40] };
const KEY = 'fiq_haptics';
let enabled = true;
try { enabled = localStorage.getItem(KEY) !== '0'; } catch { /* storage unavailable */ }
let tick: HTMLLabelElement | null = null;

export const hapticsEnabled = () => enabled;
export function setHapticsEnabled(on: boolean) { enabled = on; try { localStorage.setItem(KEY, on ? '1' : '0'); } catch { /* ignore */ } if (on) haptic('success'); }

function iosTick() {
  if (!tick) {
    tick = document.createElement('label');
    tick.setAttribute('aria-hidden', 'true');
    tick.style.cssText = 'position:fixed;left:-200px;top:-200px;opacity:0;pointer-events:none';
    const i = document.createElement('input');
    i.type = 'checkbox';
    i.setAttribute('switch', '');
    tick.appendChild(i);
    document.body.appendChild(tick);
  }
  tick.click();
}

export function haptic(kind: HapticKind | number = 'tap') {
  if (!enabled) return;
  try {
    const pattern = typeof kind === 'number' ? kind : PATTERNS[kind];
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') navigator.vibrate(pattern);
    else if (typeof document !== 'undefined') { iosTick(); if (Array.isArray(pattern) && pattern.length > 2) setTimeout(iosTick, 70); }
  } catch { /* unsupported */ }
}
