/**
 * UI primitives. Screens import ONLY from here, never raw HTML classes, so moving to Expo means re-implementing
 * this single file with React Native components (View/Text/Pressable/Animated, bottom-sheet, expo-haptics).
 * The API of each primitive is intentionally React-Native-shaped (onPress, children, no DOM events).
 */
import { ReactNode, useEffect, useRef, useState } from 'react';
import { nutriScoreColors, novaColors } from '@shared/theme';
import { t } from '@shared/i18n';

import { haptic } from '../haptics';
export { haptic };

export function Screen({ children }: { children: ReactNode }) { return <div className="screen">{children}</div>; }

export function NavBar({ title, onBack, right }: { title?: string; onBack?: () => void; right?: ReactNode }) {
  const [s, setS] = useState(false);
  useEffect(() => { const f = () => setS(window.scrollY > 36); f(); window.addEventListener('scroll', f, { passive: true }); return () => window.removeEventListener('scroll', f); }, []);
  return (
    <div className={'navbar' + (s ? ' scrolled' : '')}>
      {onBack ? <button className="back" onClick={() => { haptic('tap'); onBack(); }}>‹ {t('common.back')}</button> : <span />}
      <span className="ttl">{title}</span>
      <span style={{ marginLeft: onBack ? 0 : 'auto' }}>{right}</span>
    </div>
  );
}
export const LargeTitle = ({ children, kicker, sub }: { children: ReactNode; kicker?: string; sub?: string }) => (
  <div>{kicker && <div className="kicker">{kicker}</div>}<h1>{children}</h1>{sub && <p className="mut">{sub}</p>}</div>
);
export const Section = ({ title, children }: { title?: string; children: ReactNode }) => <>{title && <h2>{title}</h2>}{children}</>;
export const Group = ({ children }: { children: ReactNode }) => <div className="group">{children}</div>;
export function Cell({ children, onPress, chevron, image }: { children: ReactNode; onPress?: () => void; chevron?: boolean; image?: string | null }) {
  return (
    <div className={'cell' + (onPress ? ' tap' : '')} onClick={onPress ? () => { haptic(); onPress(); } : undefined}>
      {image !== undefined && image !== null && <img src={image} alt="" />}
      <div className="grow">{children}</div>{chevron && <span className="chev">›</span>}
    </div>
  );
}
export const Card = ({ children, tint }: { children: ReactNode; tint?: boolean }) => <div className={'card' + (tint ? ' tint' : '')}>{children}</div>;
export const Row = ({ children, spread, wrap }: { children: ReactNode; spread?: boolean; wrap?: boolean }) => <div className={'row' + (spread ? ' sp' : '') + (wrap ? ' wrap' : '')}>{children}</div>;
export const Muted = ({ children }: { children: ReactNode }) => <div className="mut">{children}</div>;

export function Button({ children, onPress, primary, danger, small, plain, disabled }: { children: ReactNode; onPress?: () => void; primary?: boolean; danger?: boolean; small?: boolean; plain?: boolean; disabled?: boolean }) {
  return <button className={'btn' + (primary ? ' primary' : '') + (danger ? ' danger' : '') + (small ? ' sm' : '') + (plain ? ' plain' : '')} disabled={disabled} onClick={() => { haptic(); onPress?.(); }}>{children}</button>;
}
export const Chip = ({ children, on, onPress }: { children: ReactNode; on?: boolean; onPress: () => void }) => <button className={'chip' + (on ? ' on' : '')} onClick={() => { haptic('select'); onPress(); }}>{children}</button>;
export const Chips = ({ children }: { children: ReactNode }) => <div className="chips">{children}</div>;
export const Pill = ({ children, tone }: { children: ReactNode; tone?: 'w' | 'b' | 'g' }) => <span className={'pill' + (tone ? ' ' + tone : '')}>{children}</span>;

export function Segmented({ options, value, onChange }: { options: { key: string; label: string }[]; value: string; onChange: (k: string) => void }) {
  const i = Math.max(0, options.findIndex((o) => o.key === value)), w = 100 / options.length;
  return (
    <div className="seg"><div className="thumb" style={{ width: `calc(${w}% - 2px)`, left: `calc(${i * w}% + 1px)` }} />
      {options.map((o) => <button key={o.key} onClick={() => { haptic('select'); onChange(o.key); }}>{o.label}</button>)}</div>
  );
}
export const Bar = ({ value }: { value: number }) => <div className="bar"><i style={{ width: Math.max(2, Math.min(100, value * 100)) + '%' }} /></div>;
export const Skeleton = ({ h = 16, w = '100%' }: { h?: number; w?: number | string }) => <div className="skel" style={{ height: h, width: w, margin: '8px 0' }} />;

export function NutriScore({ grade }: { grade: string | null }) {
  if (!grade) return null;
  return <span className="ns">{['a', 'b', 'c', 'd', 'e'].map((g) => <span key={g} className={g === grade ? 'on' : ''} style={{ background: nutriScoreColors[g] }}>{g.toUpperCase()}</span>)}</span>;
}

/** Animated number: counts up from the previous value (Expo: use Reanimated's useSharedValue + withTiming). */
export function CountUp({ value, format }: { value: number; format: (v: number) => string }) {
  const [v, setV] = useState(0), from = useRef(0);
  useEffect(() => {
    const a = from.current, t0 = performance.now(), D = 800; let raf = 0;
    const tick = (n: number) => { const k = Math.min(1, (n - t0) / D), e = 1 - Math.pow(1 - k, 3); setV(a + (value - a) * e); if (k < 1) raf = requestAnimationFrame(tick); else from.current = value; };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [value]);
  return <span className="big">{format(v)}</span>;
}

export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title?: string; children: ReactNode }) {
  if (!open) return null;
  return <><div className="scrim" onClick={onClose} /><div className="sheet"><div className="grab" />{title && <h3 style={{ marginBottom: 8 }}>{title}</h3>}{children}</div></>;
}
export function Toast({ text }: { text: string | null }) { return text ? <div className="toast">{text}</div> : null; }

export function NovaBadge({ group, estimated }: { group: number | null | undefined; estimated?: boolean }) {
  if (!group) return <span className="pill g">NOVA ?</span>;
  return <span className="nova" style={{ background: novaColors[group] }} title={t('nova.g' + group)}>NOVA {group}{estimated && <small className="nova-est">{t('add2.est')}</small>}</span>;
}

/** Closed-by-default section: the web twin of mobile's Collapsible (native <details>, keyboard accessible). */
export function Collapsible({ title, children, open }: { title: string; children: ReactNode; open?: boolean }) {
  return <details className="coll" open={open}><summary onClick={() => haptic('tap')}>{title}</summary><div className="coll-body">{children}</div></details>;
}

/** Large friendly header block at the top of a screen. */
export function Hero({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) {
  return <div className="hero"><h1>{title}</h1>{sub && <p>{sub}</p>}{children}</div>;
}

const BANDS = [['b', 'var(--bad)'], ['w', 'var(--warn)'], ['g2', 'var(--olive)'], ['g', 'var(--accent)']] as const;
/** Quality score on its 0-100 spectrum: four coloured bands, a marker at the score. */
export function ScoreBar({ total, label }: { total: number; label?: string }) {
  return (
    <div className="spec">
      <div className="spec-bar">{BANDS.map(([k, c]) => <i key={k} style={{ background: c }} />)}<b style={{ left: Math.max(1, Math.min(99, total)) + '%' }} /></div>
      <div className="spec-tk"><span>0</span><span>25</span><span>50</span><span>75</span><span>100</span></div>
      {label && <span className="sr">{label}</span>}
    </div>
  );
}

const TONE_VAR: Record<string, string> = { g: 'var(--accent)', g2: 'var(--olive)', w: 'var(--warn)', b: 'var(--bad)' };
/** Nutrients on their own scale, negatives and positives separated (Nutri-Score points per 100 g). */
export function NutrientScale({ items, label }: { items: any[]; label: (k: string, level: string, positive: boolean) => string }) {
  return (
    <div>
      {items.map((x) => (
        <div className="nrow" key={x.key}>
          <div className="nrow-top"><span>{label(x.key, '', x.positive)}</span><span><b>{x.value == null ? '—' : x.value + ' ' + x.unit}</b> <span className="mut sm">{label(x.key, x.level, x.positive)}</span></span></div>
          <div className="nbar"><i style={{ width: Math.max(x.points ? 6 : 0, (x.points / x.max) * 100) + '%', background: TONE_VAR[x.tone] }} /></div>
        </div>))}
    </div>
  );
}

const TONE_C: Record<string, string> = { g: 'var(--accent)', g2: 'var(--olive)', y: 'var(--clay)', w: 'var(--warn)', b: 'var(--bad)' };
/** An amount placed on its labelled scale: coloured zones from worst to best (or best to worst) and a marker at the value. */
export function AmountScale({ scale }: { scale: { value: number; max: number; zones: { from: number; to: number; tone: string }[] } }) {
  const pos = Math.max(1, Math.min(99, (scale.value / scale.max) * 100));
  return (
    <div className="amt">
      <div className="amt-bar">{scale.zones.map((z, i) => <i key={i} style={{ flex: Math.max(0.0001, z.to - z.from), background: TONE_C[z.tone] }} />)}<b style={{ left: pos + '%' }} /></div>
      <div className="amt-tk"><span>0</span><span>{Math.round(scale.max / 2)}</span><span>{scale.max}+</span></div>
    </div>
  );
}

const CHAIN_LOOK: Record<string, [string, string, string]> = {
  carrefour: ['#004E9F', '#fff', 'C'], leclerc: ['#0072BC', '#F58220', 'E.L'], intermarche: ['#E2001A', '#fff', 'I'], auchan: ['#E4002B', '#fff', 'A'], lidl: ['#FFD500', '#0050AA', 'Lidl'],
  aldi: ['#00549F', '#fff', 'A'], monoprix: ['#111', '#fff', 'M'], franprix: ['#E2001A', '#fff', 'F'], casino: ['#00A651', '#fff', 'C'], superu: ['#E30613', '#fff', 'U'], picard: ['#0057A8', '#fff', 'P'],
  biocoop: ['#7AB51D', '#fff', 'B'], naturalia: ['#00954F', '#fff', 'N'], lavieclaire: ['#009A44', '#fff', 'VC'], grandfrais: ['#E30613', '#fff', 'GF'], cora: ['#E30613', '#fff', 'C'], match: ['#E30613', '#fff', 'M'],
};
/** Chain mark: an logo image if web/public/logos/<id>.png exists (the chain's own site icon), otherwise a coloured badge in the chain's colours (not the registered logo). */
export function ChainLogo({ id, name, size = 34 }: { id: string; name?: string; size?: number }) {
  const [broken, setBroken] = useState(false);
  const [bg, fg, tx] = CHAIN_LOOK[id] ?? ['#888', '#fff', (name ?? '?').slice(0, 1)];
  if (!broken) return <img src={`/logos/${id}.png`} alt={name ?? id} width={size} height={size} style={{ borderRadius: 8, objectFit: 'contain', background: '#fff' }} onError={() => setBroken(true)} />;
  return <span className="chainmark" style={{ width: size, height: size, background: bg, color: fg, fontSize: tx.length > 2 ? size * 0.3 : tx.length > 1 ? size * 0.36 : size * 0.5 }} aria-label={name ?? id}>{tx}</span>;
}
