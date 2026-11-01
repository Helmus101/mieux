import { useEffect, useRef, useState } from 'react';
import qrcode from 'qrcode-generator';
import { t } from '@shared/i18n';
import { bandOf, demoScore, toneOf, type DemoIn, type Level } from '../landingScore';
import '../landing.css';

const PRESETS: { key: string; v: DemoIn }[] = [
  { key: 'pNut', v: { sugar: 56, sat: 11, salt: 0.1, kcal: 540, add: 'C', organic: false } },
  { key: 'pYog', v: { sugar: 4.5, sat: 2, salt: 0.1, kcal: 60, add: 'A', organic: false } },
  { key: 'pCola', v: { sugar: 10.6, sat: 0, salt: 0, kcal: 42, add: 'D', organic: false } },
  { key: 'pOil', v: { sugar: 0, sat: 14, salt: 0, kcal: 884, add: 'A', organic: true } },
];

/** Count up smoothly to a target number (landing demo only). */
function useCount(target: number, ms = 700) {
  const [n, setN] = useState(target), from = useRef(target);
  useEffect(() => {
    const a = from.current, t0 = performance.now();
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setN(target); from.current = target; return; }
    let raf = 0;
    const tick = (now: number) => { const p = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - p, 3); setN(Math.round(a + (target - a) * e)); if (p < 1) raf = requestAnimationFrame(tick); else from.current = target; };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return n;
}

function Ring({ value, size = 168, label }: { value: number; size?: number; label?: string }) {
  const r = size / 2 - 12, c = 2 * Math.PI * r, n = useCount(value);
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} className="ring-bg" />
        <circle cx={size / 2} cy={size / 2} r={r} className="ring-fg" style={{ stroke: toneOf(value), strokeDasharray: c, strokeDashoffset: c * (1 - value / 100) }} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="ring-n"><b style={{ color: toneOf(value) }}>{n}</b><span>/100</span>{label && <em>{label}</em>}</div>
    </div>);
}

/** A phone that plays the app's story on a loop: scan, score, better alternatives. */
function PhoneDemo() {
  const [step, setStep] = useState(0);
  useEffect(() => { const id = setInterval(() => setStep((s) => (s + 1) % 3), 3600); return () => clearInterval(id); }, []);
  return (
    <div className="phone" aria-hidden>
      <div className="phone-notch" />
      <div className="phone-screen">
        <div className={'ps ps-scan' + (step === 0 ? ' on' : '')}>
          <div className="bars">{Array.from({ length: 28 }, (_, i) => <i key={i} style={{ width: 2 + ((i * 7) % 4), height: 54 }} />)}</div>
          <div className="sweep" />
          <p>{t('land.ph.scan')}</p>
        </div>
        <div className={'ps ps-res' + (step === 1 ? ' on' : '')}>
          <small>{t('land.ph.example')}</small>
          <h4>{t('land.ph.product')}</h4>
          <Ring value={step === 1 ? 31 : 0} size={132} />
          <div className="chips-demo"><span className="bad">Sucres élevés</span><span className="warn">Additif modéré</span></div>
        </div>
        <div className={'ps ps-alt' + (step === 2 ? ' on' : '')}>
          <small>{t('land.ph.lead')}</small>
          {[{ n: t('land.ph.alt1'), s: 86, d: 400 }, { n: t('land.ph.alt2'), s: 58, d: 900 }].map((a, i) => (
            <div className="alt-card" key={a.n} style={{ transitionDelay: `${i * 140}ms` }}>
              <div><b>{a.n}</b><span>{t('land.ph.near', { d: a.d })}</span></div>
              <strong style={{ color: toneOf(a.s) }}>{a.s}</strong>
              <em>+{a.s - 31}</em>
            </div>))}
        </div>
      </div>
    </div>);
}

function Simulator() {
  const [v, setV] = useState<DemoIn>(PRESETS[0].v);
  const r = demoScore(v);
  const set = <K extends keyof DemoIn>(k: K, x: DemoIn[K]) => setV((o) => ({ ...o, [k]: x }));
  const sliders: { k: 'sugar' | 'sat' | 'salt' | 'kcal'; max: number; step: number; unit: string }[] = [
    { k: 'sugar', max: 60, step: 0.5, unit: 'g' }, { k: 'sat', max: 20, step: 0.5, unit: 'g' }, { k: 'salt', max: 3, step: 0.05, unit: 'g' }, { k: 'kcal', max: 900, step: 5, unit: 'kcal' }];
  const drivers = (['sugar', 'sat', 'salt', 'energy'] as const).map((k) => ({ k, p: r.drivers[k] })).sort((a, b) => b.p - a.p);
  return (
    <section className="sim reveal" id="try">
      <div className="sec-head"><h2>{t('land.simTitle')}</h2><p>{t('land.simSub')}</p></div>
      <div className="sim-grid">
        <div className="sim-ctl">
          <div className="presets" role="group" aria-label={t('land.preset')}>{PRESETS.map((p) => <button key={p.key} className="pre" onClick={() => setV(p.v)}>{t('land.' + p.key)}</button>)}</div>
          {sliders.map((s) => (
            <label key={s.k} className="sl">
              <span>{t('land.' + s.k)} <small>{t('land.per100')}</small></span>
              <input type="range" min={0} max={s.max} step={s.step} value={v[s.k]} onChange={(e) => set(s.k, Number(e.target.value))} />
              <b>{String(v[s.k]).replace('.', ',')} {s.unit}</b>
            </label>))}
          <div className="sl"><span>{t('land.additives')}</span>
            <div className="lvls">{(['A', 'B', 'C', 'D'] as Level[]).map((l) => <button key={l} className={'lvl' + (v.add === l ? ' on' : '') + ' l' + l} onClick={() => set('add', l)}>{t('addl.' + l)}</button>)}</div></div>
          <label className="tog"><input type="checkbox" checked={v.organic} onChange={(e) => set('organic', e.target.checked)} /><i /><span>{t('land.organic')}</span></label>
        </div>
        <div className="sim-out">
          <Ring value={r.total} size={208} label={t('score.' + bandOf(r.total))} />
          <div className="parts"><span>Nutrition <b>{Math.round(r.nutrition)}/60</b></span><span>Additifs <b>{Math.round(r.additives)}/30</b></span><span>Bio <b>{r.organic}/10</b></span></div>
          <div className="why"><h5>{t('land.why')}</h5>
            {drivers.map((d) => <div className="drv" key={d.k}><span>{t('land.' + (d.k === 'energy' ? 'kcal' : d.k))}</span><div><i style={{ width: `${Math.min(100, d.p * 10)}%` }} /></div><b>{d.p}</b></div>)}
          </div>
          {r.capped && <p className="capnote">{t('land.capped')}</p>}
          <p className="simnote">{t('land.simNote')}</p>
        </div>
      </div>
    </section>);
}

function Qr({ url }: { url: string }) {
  const q = qrcode(0, 'M'); q.addData(url); q.make();
  return <div className="qr" aria-label={url} dangerouslySetInnerHTML={{ __html: q.createSvgTag({ cellSize: 6, margin: 2, scalable: true }) }} />;
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {  // reveal on scroll
    const els = root.current?.querySelectorAll('.reveal') ?? [];
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: 0.15 });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
  const glow = (e: React.MouseEvent<HTMLElement>) => {  // cursor-following light + phone tilt
    const b = e.currentTarget.getBoundingClientRect(), x = (e.clientX - b.left) / b.width, y = (e.clientY - b.top) / b.height;
    e.currentTarget.style.setProperty('--mx', `${x * 100}%`); e.currentTarget.style.setProperty('--my', `${y * 100}%`);
    e.currentTarget.style.setProperty('--ry', `${(x - 0.5) * 16}deg`); e.currentTarget.style.setProperty('--rx', `${(0.5 - y) * 12}deg`);
  };
  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  const feats = [['f1t', 'f1d', 'M5 12l4 4 10-10'], ['f2t', 'f2d', 'M12 21s-7-6.2-7-11a7 7 0 0114 0c0 4.8-7 11-7 11zM12 12a2 2 0 100-4 2 2 0 000 4z'], ['f3t', 'f3d', 'M9 3h6M10 3v6l-5 9a2 2 0 002 3h10a2 2 0 002-3l-5-9V3'], ['f4t', 'f4d', 'M6 11V8a6 6 0 0112 0v3M5 11h14v10H5z']];
  return (
    <div className="landing" ref={root}>
      <header className="l-nav">
        <a className="brand" href="/" aria-label="Mieux"><img src="/favicon.svg" alt="" width={34} height={34} /><b>Mieux</b></a>
        <nav><button onClick={() => go('features')}>{t('land.navFeatures')}</button><button onClick={() => go('try')}>{t('land.navTry')}</button><button onClick={() => go('mobile')}>{t('land.navPhone')}</button></nav>
        <button className="l-cta sm" onClick={onEnter}>{t('land.open')}</button>
      </header>

      <section className="hero" onMouseMove={glow}>
        <div className="hero-glow" />
        <div className="hero-copy">
          <span className="kick">{t('land.kicker')}</span>
          <h1><span>{t('land.t1')}</span> <span>{t('land.t2')}</span> <em>{t('land.t3')}</em></h1>
          <p>{t('land.sub')}</p>
          <div className="hero-btns"><button className="l-cta" onClick={onEnter}>{t('land.open')}</button><button className="l-ghost" onClick={() => go('try')}>{t('land.demo')}</button></div>
          <small>{t('land.trust')}</small>
        </div>
        <div className="hero-phone"><PhoneDemo /></div>
        <button className="scroll" onClick={() => go('try')} aria-label={t('land.scroll')}><i /></button>
      </section>

      <Simulator />

      <section className="feats reveal" id="features">
        <div className="sec-head"><h2>{t('land.featTitle')}</h2></div>
        <div className="feat-grid">
          {feats.map(([a, b, d], i) => (
            <article className="feat" key={a} style={{ transitionDelay: `${i * 80}ms` }}>
              <svg viewBox="0 0 24 24" aria-hidden><path d={d} /></svg>
              <h3>{t('land.' + a)}</h3><p>{t('land.' + b)}</p>
            </article>))}
        </div>
      </section>

      <section className="mob reveal" id="mobile">
        <div className="mob-in">
          <div><h2>{t('land.mobTitle')}</h2><p>{t('land.mobSub')}</p><button className="l-ghost light" onClick={onEnter}>{t('land.mobOr')}</button></div>
          <Qr url={`${window.location.origin}/app`} />
        </div>
      </section>

      <footer className="l-foot"><span>{t('land.foot')}</span><button className="l-cta sm" onClick={onEnter}>{t('land.open')}</button></footer>
    </div>);
}
