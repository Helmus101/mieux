import { useEffect } from 'react';
import { isInstalled } from './install';

/**
 * Swipe in from the left edge to go back, like a native iOS screen. Only in the installed app: a browser tab already
 * has its own edge gesture, and two at once would fight. Ignored while the camera is open (the scanner is full screen).
 */
export function useEdgeSwipeBack(back: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled || !isInstalled() || !('ontouchstart' in window)) return;
    let x0 = 0, y0 = 0, t0 = 0, armed = false;
    const start = (e: TouchEvent) => {
      const t = e.touches[0];
      armed = t.clientX <= 28 && window.history.length > 1 && !document.querySelector('.cam, .sheet');
      x0 = t.clientX; y0 = t.clientY; t0 = Date.now();
    };
    const end = (e: TouchEvent) => {
      if (!armed) return; armed = false;
      const t = e.changedTouches[0], dx = t.clientX - x0, dy = Math.abs(t.clientY - y0), dt = Date.now() - t0;
      if (dx > 90 && dy < 60 && dt < 600) back();
    };
    window.addEventListener('touchstart', start, { passive: true });
    window.addEventListener('touchend', end, { passive: true });
    return () => { window.removeEventListener('touchstart', start); window.removeEventListener('touchend', end); };
  }, [back, enabled]);
}
