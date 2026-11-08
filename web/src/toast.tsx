import { useEffect, useRef, useState } from 'react';
import { create } from 'zustand';

interface Item { id: number; text: string; undo?: () => void; actionLabel?: string }
const useToasts = create<{ items: Item[] }>(() => ({ items: [] }));
let seq = 0;

/** Shows a message for a few seconds. With `undo`, the toast carries an Undo button that runs it once. */
export function toast(text: string, opts: { undo?: () => void; actionLabel?: string; ms?: number } = {}) {
  const id = ++seq;
  useToasts.setState((s) => ({ items: [...s.items.slice(-2), { id, text, undo: opts.undo, actionLabel: opts.actionLabel }] }));
  setTimeout(() => dismiss(id), opts.ms ?? (opts.undo ? 5000 : 2600));
}
const dismiss = (id: number) => useToasts.setState((s) => ({ items: s.items.filter((i) => i.id !== id) }));

function ToastCard({ item }: { item: Item }) {
  const [dx, setDx] = useState(0), start = useRef<number | null>(null);
  return (
    <div className="toast2" role="status" style={{ transform: `translateX(${dx}px)`, opacity: 1 - Math.min(1, Math.abs(dx) / 160), transition: start.current == null ? 'transform .2s, opacity .2s' : 'none' }}
      onPointerDown={(e) => { start.current = e.clientX; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); }}
      onPointerMove={(e) => { if (start.current != null) setDx(e.clientX - start.current); }}
      onPointerUp={() => { const far = Math.abs(dx) > 80; start.current = null; if (far) dismiss(item.id); else setDx(0); }}
      onPointerCancel={() => { start.current = null; setDx(0); }}>
      <span>{item.text}</span>
      {item.undo && <button onClick={() => { item.undo?.(); dismiss(item.id); }}>{item.actionLabel ?? 'Annuler'}</button>}
    </div>
  );
}

/** Mount once. Swipe a toast sideways to dismiss it. */
export function ToastHost() {
  const items = useToasts((s) => s.items);
  useEffect(() => undefined, []);
  return <div className="toasts" aria-live="polite">{items.map((i) => <ToastCard key={i.id} item={i} />)}</div>;
}
