import { useEffect, useMemo, useRef, useState } from 'react';
import { t } from '@shared/i18n';
import { routes, useNav } from './nav';

interface Cmd { label: string; hint?: string; run: () => void }

/** Command menu: Ctrl/⌘ + K (or "/") opens it; type to filter, ↑↓ to move, Enter to run, Esc to close. Each entry shows its shortcut. */
export default function CommandMenu() {
  const { go } = useNav();
  const [open, setOpen] = useState(false), [q, setQ] = useState(''), [i, setI] = useState(0), input = useRef<HTMLInputElement>(null);
  const cmds: Cmd[] = useMemo(() => [
    { label: t('tabs.scan'), hint: 'G S', run: () => go(routes.scan) },
    { label: t('tabs.list'), hint: 'G L', run: () => go(routes.list) },
    { label: t('tabs.profile'), hint: 'G P', run: () => go(routes.profile) },
    { label: t('tabs.compare'), hint: 'G C', run: () => go(routes.compare) },
    { label: t('history.title') || 'Historique', hint: 'G H', run: () => go(routes.history) },
  ], [go]);
  const shown = cmds.filter((c) => c.label.toLowerCase().includes(q.toLowerCase()));

  useEffect(() => {
    let g = 0;
    const onKey = (e: KeyboardEvent) => {
      const typing = /input|textarea|select/i.test((e.target as HTMLElement)?.tagName ?? '') || (e.target as HTMLElement)?.isContentEditable;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen((o) => !o); setQ(''); setI(0); return; }
      if (typing) return;
      if (e.key === '/') { e.preventDefault(); setOpen(true); setQ(''); setI(0); return; }
      if (e.key === 'Escape') { setOpen(false); return; }
      if (g && Date.now() - g < 900) {        // "g" then a letter: go to a screen
        const m = { s: routes.scan, l: routes.list, p: routes.profile, c: routes.compare, h: routes.history }[e.key.toLowerCase()];
        g = 0; if (m) go(m); return;
      }
      if (e.key.toLowerCase() === 'g') g = Date.now();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go]);
  useEffect(() => { if (open) setTimeout(() => input.current?.focus(), 0); }, [open]);
  if (!open) return null;
  const run = (c?: Cmd) => { if (c) { setOpen(false); c.run(); } };
  return (
    <div className="cmdk-back" onClick={() => setOpen(false)}>
      <div className="cmdk" role="dialog" aria-label="Menu de commandes" onClick={(e) => e.stopPropagation()}>
        <input ref={input} value={q} placeholder="Aller à…" onChange={(e) => { setQ(e.target.value); setI(0); }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setI((n) => Math.min(shown.length - 1, n + 1)); }
            else if (e.key === 'ArrowUp') { e.preventDefault(); setI((n) => Math.max(0, n - 1)); }
            else if (e.key === 'Enter') run(shown[i]);
            else if (e.key === 'Escape') setOpen(false);
          }} />
        {shown.map((c, n) => <button key={c.label} className={n === i ? 'on' : ''} onMouseEnter={() => setI(n)} onClick={() => run(c)}><span>{c.label}</span>{c.hint && <kbd>{c.hint}</kbd>}</button>)}
        {!shown.length && <p className="mut sm" style={{ padding: 12 }}>—</p>}
      </div>
    </div>
  );
}
