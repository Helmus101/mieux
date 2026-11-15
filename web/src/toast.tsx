import { useEffect } from 'react';
import { useSpringDrag } from './spring';
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
  // Follows the finger sideways; a flick either way carries it off (momentum-projected), a gentle pull springs back.
  const { ref } = useSpringDrag<HTMLDivElement>({
    axis: 'x', response: 0.3, bounce: 0.1, snaps: () => [-window.innerWidth, 0, window.innerWidth],
    onMove: (x) => { if (ref.current) ref.current.style.opacity = String(1 - Math.min(1, Math.abs(x) / 160)); },
    onSettle: (pt) => { if (pt !== 0) dismiss(item.id); },
  });
  return (
    <div ref={ref} className="toast2" role="status">
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
