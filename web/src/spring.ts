import { useEffect, useRef } from 'react';

/**
 * Fluid-motion toolkit (Apple's "Designing Fluid Interfaces", for the web). No dependency.
 *  - springs take Apple's two knobs: `damping` (1 = no overshoot) and `response` (seconds, not a duration);
 *  - a spring always starts from the value on screen and from the finger's velocity, so it can be grabbed mid-flight;
 *  - `project` throws a flick forward to where it would come to rest, `rubberband` softens the edges.
 */

export const reducedMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Where a release at `velocity` (px/s) would come to rest, like scroll deceleration. */
export const project = (velocity: number, rate = 0.998) => (velocity / 1000) * rate / (1 - rate);

/** Progressive resistance past an edge: the further you pull, the less the element follows. */
export const rubberband = (overshoot: number, dimension: number, c = 0.55) =>
  Math.sign(overshoot) * (Math.abs(overshoot) * dimension * c) / (dimension + c * Math.abs(overshoot));

/** The point in `points` closest to `x`. */
export const nearest = (x: number, points: number[]) => points.reduce((a, b) => (Math.abs(b - x) < Math.abs(a - x) ? b : a));

export interface SpringOpts { damping?: number; response?: number; velocity?: number; onUpdate: (x: number) => void; onDone?: () => void }
export interface Spring { stop: () => number; value: () => number; velocity: () => number }

/** Animates from `from` to `to`. Returns a handle: `stop()` freezes it where it is and returns the live value. */
export function spring(from: number, to: number, { damping = 1, response = 0.35, velocity = 0, onUpdate, onDone }: SpringOpts): Spring {
  let x = from, v = velocity, raf = 0, last = performance.now(), live = true;
  const w = (2 * Math.PI) / response, k = w * w, c = 2 * damping * w;   // stiffness, damping coefficient (unit mass)
  const settle = () => { live = false; x = to; v = 0; onUpdate(to); onDone?.(); };
  if (reducedMotion()) { settle(); return { stop: () => x, value: () => x, velocity: () => 0 }; }
  const tick = (now: number) => {
    if (!live) return;
    let dt = Math.min(0.032, (now - last) / 1000); last = now;
    while (dt > 0) { const h = Math.min(dt, 0.004); v += (-k * (x - to) - c * v) * h; x += v * h; dt -= h; }   // small fixed steps stay stable
    if (Math.abs(v) < 0.5 && Math.abs(x - to) < 0.3) { settle(); return; }
    onUpdate(x); raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
  return { stop: () => { live = false; cancelAnimationFrame(raf); return x; }, value: () => x, velocity: () => v };
}

/** Last ~100 ms of pointer samples, for the velocity at release. */
export class Tracker {
  private s: { p: number; t: number }[] = [];
  reset() { this.s = []; }
  add(p: number, t = performance.now()) { this.s.push({ p, t }); while (this.s.length > 2 && t - this.s[0].t > 100) this.s.shift(); }
  /** px/s */
  get velocity() { const a = this.s[0], b = this.s[this.s.length - 1]; return !a || b.t === a.t ? 0 : ((b.p - a.p) / (b.t - a.t)) * 1000; }
}

interface DragOpts {
  axis: 'x' | 'y';
  /** Where the element can rest, as offsets from its natural place (e.g. [0, height] for a sheet that can be dismissed). */
  snaps: () => number[];
  /** Called when it comes to rest on a snap point (after a flick, `index` is the one it was thrown to). */
  onSettle?: (point: number) => void;
  /** Called on every frame with the live offset (for the scrim, opacity, etc.). */
  onMove?: (offset: number) => void;
  /** Springs that carry a flick may overshoot a little; a plain release does not. */
  bounce?: number;
  response?: number;
  /** Pointer must travel this far before the drag claims the gesture. */
  slop?: number;
  /** Return false to let the gesture pass (e.g. a scrolled sheet). */
  canStart?: (e: PointerEvent) => boolean;
}

/**
 * Makes an element draggable along one axis with 1:1 tracking, rubber-banding past its outermost snap points,
 * momentum projection on release and a velocity-carrying spring to the chosen snap point. Interruptible: grabbing it
 * mid-spring picks it up where it is. Writes `transform` directly (no React renders per frame).
 * Returns `animateTo(point)` to move it programmatically (entry, close button) with the same spring.
 */
export function useSpringDrag<T extends HTMLElement>(opts: DragOpts) {
  const ref = useRef<T>(null), o = useRef(opts); o.current = opts;
  const pos = useRef(0), anim = useRef<Spring | null>(null);
  const apply = (v: number) => { pos.current = v; const el = ref.current; if (el) el.style.transform = v ? (o.current.axis === 'x' ? `translate3d(${v}px,0,0)` : `translate3d(0,${v}px,0)`) : ''; o.current.onMove?.(v); };
  const animateTo = (to: number, velocity = 0, bounce = 0) => {
    anim.current?.stop();
    anim.current = spring(pos.current, to, { damping: 1 - bounce, response: o.current.response ?? 0.35, velocity, onUpdate: apply, onDone: () => { anim.current = null; o.current.onSettle?.(to); } });
  };
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const tr = new Tracker();
    let id = -1, grab = 0, claimed = false, c0 = 0;
    const coord = (e: PointerEvent) => (o.current.axis === 'x' ? e.clientX : e.clientY);
    const down = (e: PointerEvent) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      if (o.current.canStart && !o.current.canStart(e)) return;
      id = e.pointerId; c0 = coord(e); claimed = false; tr.reset(); tr.add(c0);
      const live = anim.current?.stop();                     // interrupt: start from what is on screen, not from the target
      if (live !== undefined) { anim.current = null; pos.current = live; claimed = true; grab = pos.current - c0; el.setPointerCapture(id); }
    };
    const move = (e: PointerEvent) => {
      if (e.pointerId !== id) return;
      const c = coord(e);
      if (!claimed) {
        if (Math.abs(c - c0) < (o.current.slop ?? 8)) return;
        claimed = true; grab = pos.current - c; el.setPointerCapture(id);   // respect where the finger grabbed: no jump on claim
      }
      tr.add(c);
      const raw = c + grab, pts = o.current.snaps(), lo = Math.min(...pts), hi = Math.max(...pts), dim = Math.max(1, hi - lo, 200);
      apply(raw < lo ? lo + rubberband(raw - lo, dim) : raw > hi ? hi + rubberband(raw - hi, dim) : raw);
    };
    const up = (e: PointerEvent) => {
      if (e.pointerId !== id) return; id = -1;
      if (!claimed) return;
      claimed = false;
      const v = tr.velocity, pts = o.current.snaps();
      const target = nearest(pos.current + project(v), pts);   // where the flick is going, not where the finger let go
      const flicked = Math.abs(v) > 300;
      animateTo(target, v, flicked && o.current.bounce ? o.current.bounce : 0);
    };
    el.addEventListener('pointerdown', down); el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    return () => { el.removeEventListener('pointerdown', down); el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); anim.current?.stop(); };
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return { ref, animateTo, set: apply, position: () => pos.current };
}
